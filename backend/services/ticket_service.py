import json
import logging
import re
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.llm_provider import LLMProvider
from models.schemas import (
    TicketCreate,
    TicketDetailResponse,
    TicketDraftSuggestion,
    TicketHistoryResponse,
    TicketMessageCreate,
    TicketMessageResponse,
    TicketResponse,
    TicketStatus,
    TicketUpdate,
)

logger = logging.getLogger(__name__)

PRIORITY_TO_VALUE = {
    "urgent": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
}

PRIORITY_TO_CRITICALITY = {
    "urgent": "très haute",
    "high": "haute",
    "medium": "moyenne",
    "low": "basse",
}

STATUS_TO_LEGACY = {
    "open": "nouveau",
    "in progress": "en_cours",
    "waiting for user": "en_cours",
    "resolved": "resolu",
    "closed": "clos",
}

LEGACY_STATUS_TO_LABEL = {
    "nouveau": "Open",
    "en_cours": "In Progress",
    "resolu": "Resolved",
    "clos": "Closed",
}

TECHNICIAN_GROUPS = {
    "Amine Zinoun": {
        "email": "amine.spk.zinoun@gmail.com",
        "role": "Support IT",
        "categories": ("Wincar", "Windows", "GestorNet", "Consommable", "Moovapps", "Contrat de Vente", "GENERAFI", "Fidélisation", "SMS", "VOXCO", "TPE"),
    },
    "Sofia El Idrissi": {
        "email": "sofia.elidrissi@autohall.ma",
        "role": "Support IT",
        "categories": ("Citrix", "Logiciel Système", "Réseau", "CRM", "Ligne VPN", "RIAPP", "Qalitel Doc", "Microsoft Teams", "VPN_FortiClient", "Antivirus", "Intranet", "eSeller"),
    },
    "Youssef Bensaid": {
        "email": "youssef.bensaid@autohall.ma",
        "role": "Support IT",
        "categories": ("Matériel", "Internet", "APPCC", "Poste IP Phone", "Reporting", "PayRoll", "GDoc", "Site Web", "Optimmo", "Qalitel Compar", "SLV", "C.Conformité"),
    },
    "Nabil Cherkaoui": {
        "email": "nabil.cherkaoui@autohall.ma",
        "role": "Support IT",
        "categories": ("Messagerie", "Sage", "Outillages SAV", "Auto Naps", "Ligne Téléphonique", "GSM", "Sage Paie & RH", "WebEX", "AppGCMA", "SRM", "Devopps", "OPEL"),
    },
}

TECHNICIAN_BY_CATEGORY = {
    category: {"name": technician_name, "email": details["email"], "role": details["role"]}
    for technician_name, details in TECHNICIAN_GROUPS.items()
    for category in details["categories"]
}


class TicketService:
    """CRUD et enrichissement des tickets helpdesk."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _clean_text(self, text: str) -> str:
        """
        Nettoie le texte : supprime les salutations, les répétitions,
        les espaces superflus.
        """
        if not text:
            return text

        # 1. Supprimer les salutations en début de phrase
        greetings = (
            r'^bonjour\s*[,;.!?:]?\s*',
            r'^salut\s*[,;.!?:]?\s*',
            r'^hello\s*[,;.!?:]?\s*',
            r'^coucou\s*[,;.!?:]?\s*',
            r'^salam\s*[,;.!?:]?\s*',
            r'^hi\s*[,;.!?:]?\s*',
        )
        for pattern in greetings:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # 2. Supprimer les espaces multiples
        text = ' '.join(text.split())

        # 3. Supprimer les répétitions consécutives de phrases (ex: "contacter le support contacter le support")
        sentences = re.split(r'(?<=[.!?])\s+', text)
        seen = set()
        cleaned_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            key = re.sub(r'[.!?]+$', '', sent).lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned_sentences.append(sent)

        text = '. '.join(cleaned_sentences)
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        return text

    def _normalize_priority(self, priority: str) -> tuple[str, int]:
        normalized = priority.strip().lower()
        if normalized not in PRIORITY_TO_VALUE:
            normalized = "medium"
        return normalized.capitalize(), PRIORITY_TO_VALUE[normalized]

    def _normalize_status(self, status: str) -> tuple[str, str]:
        normalized = status.strip().lower()
        if normalized not in STATUS_TO_LEGACY:
            normalized = "open"
        return normalized.title(), STATUS_TO_LEGACY[normalized]

    @staticmethod
    def get_default_technician_for_category(category: Optional[str]) -> Optional[Dict[str, str]]:
        if not category:
            return None
        normalized = category.strip()
        for known_category, technician in TECHNICIAN_BY_CATEGORY.items():
            if known_category.lower() == normalized.lower():
                return technician
        return None

    def _select_clause(self) -> str:
        return """
            SELECT
                t.id,
                t.title,
                COALESCE(t.description, t.content, '') AS description,
                COALESCE(t.category, c.name, 'General') AS category,
                COALESCE(t.priority_label,
                    CASE
                        WHEN t.priority <= 1 THEN 'Urgent'
                        WHEN t.priority = 2 THEN 'High'
                        WHEN t.priority = 3 THEN 'Medium'
                        ELSE 'Low'
                    END
                ) AS priority,
                COALESCE(t.status_label,
                    CASE t.status
                        WHEN 'nouveau' THEN 'Open'
                        WHEN 'en_cours' THEN 'In Progress'
                        WHEN 'resolu' THEN 'Resolved'
                        WHEN 'clos' THEN 'Closed'
                        ELSE 'Open'
                    END
                ) AS status,
                COALESCE(t.type, 1) AS ticket_type,
                COALESCE(t.criticality, 'moyenne') AS criticality,
                COALESCE(t.priority, CASE
                    WHEN t.priority_label = 'Urgent' THEN 1
                    WHEN t.priority_label = 'High' THEN 2
                    WHEN t.priority_label = 'Medium' THEN 3
                    ELSE 4
                END) AS priority_value,
                t.user_name,
                t.user_email,
                t.conversation_id,
                t.assigned_to_id,
                t.assigned_to_name,
                t.assigned_to_email,
                t.assigned_at,
                t.created_at,
                t.updated_at,
                COALESCE(t.resolved_at, t.solved_at) AS resolved_at
            FROM tickets t
            LEFT JOIN categories c ON c.id = t.category_id
        """

    def _row_to_ticket(self, row) -> TicketResponse:
        data = row._mapping
        return TicketResponse(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            category=data["category"],
            priority=data["priority"],
            status=data["status"],
            ticket_type=data.get("ticket_type", 1),
            criticality=data.get("criticality"),
            priority_value=data.get("priority_value"),
            user_name=data.get("user_name"),
            user_email=data.get("user_email"),
            conversation_id=data.get("conversation_id"),
            assigned_to_id=data.get("assigned_to_id"),
            assigned_to_name=data.get("assigned_to_name"),
            assigned_to_email=data.get("assigned_to_email"),
            assigned_at=data.get("assigned_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            resolved_at=data.get("resolved_at"),
        )

    async def create_ticket(self, data: Dict[str, Any]) -> Tuple[TicketResponse, bool]:
        """
        Crée un nouveau ticket. Retourne (TicketResponse, True).
        (La logique de mise à jour par conversation_id a été supprimée pour éviter
        de réutiliser le même ticket pour des problèmes différents.)
        """
        priority_label, priority_value = self._normalize_priority(data["priority"])
        status_label, legacy_status = self._normalize_status(data.get("status", "Open"))

        technician = self.get_default_technician_for_category(data.get("category"))
        assigned_to_name = data.get("assigned_to_name") or (technician["name"] if technician else None)
        assigned_to_email = data.get("assigned_to_email") or (technician["email"] if technician else None)

        query = text(
            """
            INSERT INTO tickets (
                title, content, description, category, type, priority, priority_label,
                criticality, status, status_label, user_name, user_email, conversation_id,
                summary, resolved_at, assigned_to_name, assigned_to_email, assigned_at
            )
            VALUES (
                :title, :content, :description, :category, :ticket_type, :priority_value, :priority_label,
                :criticality, :legacy_status, :status_label, :user_name, :user_email, :conversation_id,
                :summary, :resolved_at, :assigned_to_name, :assigned_to_email, CURRENT_TIMESTAMP
            )
            RETURNING id
            """
        )

        params = {
            "title": data["title"],
            "content": data["description"],
            "description": data["description"],
            "category": data["category"],
            "ticket_type": int(data.get("ticket_type", 1)),
            "priority_value": priority_value,
            "priority_label": priority_label,
            "criticality": data.get("criticality") or PRIORITY_TO_CRITICALITY[priority_label.lower()],
            "legacy_status": legacy_status,
            "status_label": status_label,
            "user_name": data.get("user_name"),
            "user_email": data["user_email"],
            "conversation_id": data.get("conversation_id"),
            "summary": data.get("summary"),
            "resolved_at": data.get("resolved_at"),
            "assigned_to_name": assigned_to_name,
            "assigned_to_email": assigned_to_email,
        }

        result = await self.db.execute(query, params)
        row = result.fetchone()
        ticket_id = row._mapping["id"]
        await self.db.commit()

        if assigned_to_email:
            tech_query = text(
                """
                SELECT id, full_name, email, role, team, category_id, active, created_at
                FROM technicians
                WHERE LOWER(email) = LOWER(:email)
                LIMIT 1
                """
            )
            tech_result = await self.db.execute(tech_query, {"email": assigned_to_email})
            tech_row = tech_result.fetchone()
            if tech_row:
                await self.db.execute(
                    text(
                        """
                        INSERT INTO ticket_assignments (ticket_id, technician_id, assigned_by, reason, assigned_at)
                        VALUES (:ticket_id, :technician_id, :assigned_by, :reason, CURRENT_TIMESTAMP)
                        """
                    ),
                    {
                        "ticket_id": ticket_id,
                        "technician_id": tech_row._mapping["id"],
                        "assigned_by": "system",
                        "reason": f"Auto-assignment by category: {data.get('category')}",
                    },
                )
                await self.db.commit()

        return await self.get_ticket(ticket_id), True

    async def assign_ticket(
        self,
        ticket_id: int,
        technician_id: Optional[int] = None,
        technician_email: Optional[str] = None,
        technician_name: Optional[str] = None,
        assigned_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[TicketResponse]:
        current = await self.get_ticket(ticket_id)
        if not current:
            return None

        tech_row = None

        if technician_id is not None:
            tech_result = await self.db.execute(
                text("SELECT id, full_name, email FROM technicians WHERE id = :tech_id LIMIT 1"),
                {"tech_id": technician_id}
            )
            tech_row = tech_result.fetchone()

        if tech_row is None and technician_email is not None:
            tech_result = await self.db.execute(
                text("SELECT id, full_name, email FROM technicians WHERE LOWER(email) = LOWER(:tech_email) LIMIT 1"),
                {"tech_email": technician_email}
            )
            tech_row = tech_result.fetchone()

        if not tech_row:
            return None

        tech_mapping = tech_row._mapping
        new_name = technician_name or tech_mapping.get("full_name")
        new_email = technician_email or tech_mapping.get("email")

        update_query = text(
            """
            UPDATE tickets
            SET assigned_to_id = :tech_id,
                assigned_to_name = :tech_name,
                assigned_to_email = :tech_email,
                assigned_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :ticket_id
            RETURNING id
            """
        )
        await self.db.execute(
            update_query,
            {
                "tech_id": tech_mapping["id"],
                "tech_name": new_name,
                "tech_email": new_email,
                "ticket_id": ticket_id,
            },
        )

        await self.db.execute(
            text(
                """
                INSERT INTO ticket_assignments (ticket_id, technician_id, assigned_by, reason, assigned_at)
                VALUES (:ticket_id, :technician_id, :assigned_by, :reason, CURRENT_TIMESTAMP)
                """
            ),
            {
                "ticket_id": ticket_id,
                "technician_id": tech_mapping["id"],
                "assigned_by": assigned_by or "system",
                "reason": reason or "Manual assignment",
            },
        )
        await self.db.commit()
        return await self.get_ticket(ticket_id)

    async def get_ticket(self, ticket_id: int) -> Optional[TicketResponse]:
        query = text(f"{self._select_clause()} WHERE t.id = :id")
        result = await self.db.execute(query, {"id": ticket_id})
        row = result.fetchone()
        if row:
            return self._row_to_ticket(row)
        return None

    async def get_ticket_detail(self, ticket_id: int) -> Optional[TicketDetailResponse]:
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        messages = await self.get_ticket_messages(ticket_id)
        history = await self.get_ticket_history(ticket_id)
        return TicketDetailResponse(**ticket.model_dump(), messages=messages, history=history)

    async def get_ticket_status(self, ticket_id: int) -> Optional[TicketStatus]:
        query = text(
            """
            SELECT id,
                   COALESCE(status_label,
                        CASE status
                            WHEN 'nouveau' THEN 'Open'
                            WHEN 'en_cours' THEN 'In Progress'
                            WHEN 'resolu' THEN 'Resolved'
                            WHEN 'clos' THEN 'Closed'
                            ELSE 'Open'
                        END
                   ) AS status,
                   updated_at,
                   COALESCE(resolved_at, solved_at) AS resolved_at
            FROM tickets WHERE id = :id
            """
        )
        result = await self.db.execute(query, {"id": ticket_id})
        row = result.fetchone()
        if row:
            return TicketStatus(**row._mapping)
        return None

    async def list_tickets(
        self,
        user_email: Optional[str] = None,
        assigned_to_email: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[TicketResponse]:
        query = self._select_clause()
        filters = []
        params: Dict[str, Any] = {}

        if user_email:
            filters.append("t.user_email = :user_email")
            params["user_email"] = user_email

        if assigned_to_email:
            filters.append("LOWER(t.assigned_to_email) = LOWER(:assigned_to_email)")
            params["assigned_to_email"] = assigned_to_email

        if status:
            filters.append("LOWER(COALESCE(t.status_label, t.status)) = LOWER(:status)")
            params["status"] = status

        if priority:
            filters.append("LOWER(COALESCE(t.priority_label, 'Medium')) = LOWER(:priority)")
            params["priority"] = priority

        if search:
            filters.append(
                "(t.title ILIKE :search OR COALESCE(t.description, t.content, '') ILIKE :search OR COALESCE(t.category, c.name, '') ILIKE :search OR COALESCE(t.user_name, '') ILIKE :search OR COALESCE(t.user_email, '') ILIKE :search)"
            )
            params["search"] = f"%{search}%"

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY t.updated_at DESC, t.created_at DESC"
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        return [self._row_to_ticket(row) for row in rows]

    async def update_ticket(self, ticket_id: int, updates: TicketUpdate, changed_by: Optional[str] = None) -> Optional[TicketResponse]:
        current = await self.get_ticket(ticket_id)
        if not current:
            return None

        patch = updates.model_dump(exclude_unset=True)
        if not patch:
            return current

        update_sets = []
        params: Dict[str, Any] = {"id": ticket_id}

        def add_history(field_name: str, old_value: Any, new_value: Any):
            if old_value == new_value:
                return
            history_entries.append(
                {
                    "ticket_id": ticket_id,
                    "field_name": field_name,
                    "old_value": None if old_value is None else str(old_value),
                    "new_value": None if new_value is None else str(new_value),
                    "changed_by": changed_by,
                }
            )

        history_entries: List[Dict[str, Any]] = []

        if "title" in patch:
            update_sets.append("title = :title")
            params["title"] = patch["title"]
            add_history("title", current.title, patch["title"])

        if "description" in patch:
            update_sets.append("description = :description, content = :description")
            params["description"] = patch["description"]
            add_history("description", current.description, patch["description"])

        if "category" in patch:
            update_sets.append("category = :category")
            params["category"] = patch["category"]
            add_history("category", current.category, patch["category"])

        if "priority" in patch:
            priority_label, priority_value = self._normalize_priority(patch["priority"])
            update_sets.append("priority = :priority_value, priority_label = :priority_label")
            params["priority_value"] = priority_value
            params["priority_label"] = priority_label
            update_sets.append("criticality = :criticality")
            params["criticality"] = PRIORITY_TO_CRITICALITY[priority_label.lower()]
            add_history("priority", current.priority, priority_label)

        if "status" in patch:
            status_label, legacy_status = self._normalize_status(patch["status"])
            update_sets.append("status = :legacy_status, status_label = :status_label")
            params["legacy_status"] = legacy_status
            params["status_label"] = status_label
            add_history("status", current.status, status_label)

            if status_label in {"Resolved", "Closed"}:
                update_sets.append("resolved_at = COALESCE(resolved_at, CURRENT_TIMESTAMP)")

        if "user_name" in patch:
            update_sets.append("user_name = :user_name")
            params["user_name"] = patch["user_name"]
            add_history("user_name", current.user_name, patch["user_name"])

        if "user_email" in patch:
            update_sets.append("user_email = :user_email")
            params["user_email"] = patch["user_email"]
            add_history("user_email", current.user_email, patch["user_email"])

        if "resolved_at" in patch:
            update_sets.append("resolved_at = :resolved_at")
            params["resolved_at"] = patch["resolved_at"]
            add_history("resolved_at", current.resolved_at, patch["resolved_at"])

        if not update_sets:
            return current

        update_sets.append("updated_at = CURRENT_TIMESTAMP")
        query = text(
            f"""
            UPDATE tickets
            SET {', '.join(update_sets)}
            WHERE id = :id
            RETURNING id
            """
        )
        await self.db.execute(query, params)

        if history_entries:
            history_query = text(
                """
                INSERT INTO ticket_history (ticket_id, field_name, old_value, new_value, changed_by)
                VALUES (:ticket_id, :field_name, :old_value, :new_value, :changed_by)
                """
            )
            for entry in history_entries:
                await self.db.execute(history_query, entry)

        await self.db.commit()
        return await self.get_ticket(ticket_id)

    async def update_ticket_status(self, ticket_id: int, new_status: str) -> Optional[TicketResponse]:
        return await self.update_ticket(ticket_id, TicketUpdate(status=new_status))

    async def get_ticket_messages(self, ticket_id: int) -> List[TicketMessageResponse]:
        query = text(
            """
            SELECT id, ticket_id, sender_role, sender_name, content, created_at
            FROM ticket_messages
            WHERE ticket_id = :ticket_id
            ORDER BY created_at ASC, id ASC
            """
        )
        result = await self.db.execute(query, {"ticket_id": ticket_id})
        return [TicketMessageResponse(**row._mapping) for row in result.fetchall()]

    async def add_ticket_message(self, ticket_id: int, payload: TicketMessageCreate) -> Optional[TicketMessageResponse]:
        query = text(
            """
            INSERT INTO ticket_messages (ticket_id, sender_role, sender_name, content)
            VALUES (:ticket_id, :sender_role, :sender_name, :content)
            RETURNING id, ticket_id, sender_role, sender_name, content, created_at
            """
        )
        result = await self.db.execute(
            query,
            {
                "ticket_id": ticket_id,
                "sender_role": payload.sender_role,
                "sender_name": payload.sender_name,
                "content": payload.content,
            },
        )
        row = result.fetchone()
        await self.db.execute(
            text(
                """
                INSERT INTO ticket_history (ticket_id, field_name, old_value, new_value, changed_by)
                VALUES (:ticket_id, 'message', NULL, :new_value, :changed_by)
                """
            ),
            {
                "ticket_id": ticket_id,
                "new_value": payload.content,
                "changed_by": payload.sender_name or payload.sender_role,
            },
        )
        await self.db.execute(
            text("UPDATE tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": ticket_id},
        )
        await self.db.commit()
        return TicketMessageResponse(**row._mapping) if row else None

    async def get_ticket_history(self, ticket_id: int) -> List[TicketHistoryResponse]:
        query = text(
            """
            SELECT id, ticket_id, field_name, old_value, new_value, changed_by, created_at
            FROM ticket_history
            WHERE ticket_id = :ticket_id
            ORDER BY created_at ASC, id ASC
            """
        )
        result = await self.db.execute(query, {"ticket_id": ticket_id})
        return [TicketHistoryResponse(**row._mapping) for row in result.fetchall()]

    async def suggest_from_conversation(
            self,
            llm: LLMProvider,
            conversation_messages: List[Dict[str, str]],
            user_name: Optional[str] = None,
            user_email: Optional[str] = None,
        ) -> TicketDraftSuggestion:
            transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_messages])
            prompt = (
                "Tu es un assistant helpdesk AUTOHALL. À partir de la conversation ci-dessous, "
                "propose un ticket prêt à créer. Réponds uniquement avec un JSON valide contenant "
                "les clés suivantes:\n"
                "- title: titre court du problème (max 80 caractères)\n"
                "- description: description technique concise du problème (max 3 phrases, PAS toute la conversation)\n"
                "- category: catégorie parmi: Wincar, Messagerie, Citrix, Matériel, Internet, Logiciel Système, Sage, Windows, APPCC, Réseau, Outillages SAV, GestorNet, CRM, Auto Naps, Poste IP Phone, Reporting, Ligne VPN, Consommable, Ligne Téléphonique, GSM, Moovapps, PayRoll, SRM\n"
                "- priority: Low, Medium, High ou Urgent\n"
                "- summary: résumé en 1 phrase de ce que l'utilisateur a signalé\n\n"
                "IMPORTANT: description = le problème technique en 2-3 phrases MAX. "
                "Ne copie JAMAIS toute la conversation dans description.\n\n"
                f"Conversation:\n{transcript}\n\n"
                f"Contexte utilisateur: nom={user_name or 'inconnu'}, email={user_email or 'inconnu'}"
            )
            result = await llm.chat([{"role": "user", "content": prompt}], temperature=0.2)
            result = result.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                data = json.loads(result)
            except Exception:
                try:
                    start = result.index("{")
                    end = result.rindex("}") + 1
                    candidate = result[start:end]
                    data = json.loads(candidate)
                except Exception:
                    # Fallback: utiliser le dernier message utilisateur et le nettoyer
                    last_msg = conversation_messages[-1]['content'] if conversation_messages else ''
                    cleaned = self._clean_text(last_msg)
                    return TicketDraftSuggestion(
                        title=cleaned[:80] or "Ticket AUTOHALL",
                        description=cleaned[:300] if cleaned else '',
                        category='General',
                        priority='Medium',
                        summary=cleaned[:200] if cleaned else '',
                    )
            # Post-process: nettoyer titre, description, résumé
            title = data.get("title", "Ticket issu de conversation")
            title = self._clean_text(title)
            description = data.get("description", "")[:500]
            description = self._clean_text(description)
            summary = data.get("summary", "")
            summary = self._clean_text(summary)
            return TicketDraftSuggestion(
                title=title,
                description=description,
                category=data.get("category", "General"),
                priority=data.get("priority", "Medium"),
                summary=summary,
            )

    async def create_ticket_from_suggestion(
        self,
        suggestion: TicketDraftSuggestion,
        user_email: str,
        user_name: Optional[str] = None,
        conversation_id: Optional[int] = None,
        ticket_type: int = 1,
    ) -> Tuple[TicketResponse, bool]:
        return await self.create_ticket(
            {
                "title": suggestion.title,
                "description": suggestion.description,
                "category": suggestion.category,
                "priority": suggestion.priority,
                "status": "Open",
                "ticket_type": ticket_type,
                "criticality": PRIORITY_TO_CRITICALITY[suggestion.priority.lower()],
                "user_name": user_name,
                "user_email": user_email,
                "conversation_id": conversation_id,
                "summary": suggestion.summary,
            }
        )