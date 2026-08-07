import json
import logging
from typing import List, Optional, Dict, Any

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


class TicketService:
    """CRUD et enrichissement des tickets helpdesk."""

    def __init__(self, db: AsyncSession):
        self.db = db

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
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            resolved_at=data.get("resolved_at"),
        )

    async def create_ticket(self, data: Dict[str, Any]) -> TicketResponse:
        priority_label, priority_value = self._normalize_priority(data["priority"])
        status_label, legacy_status = self._normalize_status(data.get("status", "Open"))

        query = text(
            """
            INSERT INTO tickets (
                title, content, description, category, type, priority, priority_label,
                criticality, status, status_label, user_name, user_email, conversation_id,
                summary, resolved_at
            )
            VALUES (
                :title, :content, :description, :category, :ticket_type, :priority_value, :priority_label,
                :criticality, :legacy_status, :status_label, :user_name, :user_email, :conversation_id,
                :summary, :resolved_at
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
        }

        result = await self.db.execute(query, params)
        row = result.fetchone()
        ticket_id = row._mapping["id"]
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
            "les clés: title, description, category, priority, summary. Priority doit être l'une des valeurs: Low, Medium, High, Urgent.\n\n"
            f"Conversation:\n{transcript}\n\n"
            f"Contexte utilisateur: nom={user_name or 'inconnu'}, email={user_email or 'inconnu'}"
        )
        result = await llm.chat([{"role": "user", "content": prompt}], temperature=0.2)
        result = result.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            data = json.loads(result)
        except Exception:
            # Try to recover JSON embedded in surrounding text (common when LLM adds commentary)
            try:
                start = result.index("{")
                end = result.rindex("}") + 1
                candidate = result[start:end]
                data = json.loads(candidate)
            except Exception:
                # Fallback to a conservative suggestion when parsing fails
                return TicketDraftSuggestion(
                    title=(conversation_messages[-1]['content'][:80] if conversation_messages else 'Ticket AUTOHALL'),
                    description=(conversation_messages[-1]['content'] if conversation_messages else ''),
                    category='General',
                    priority='Medium',
                    summary=(conversation_messages[-1]['content'][:200] if conversation_messages else ''),
                )
        return TicketDraftSuggestion(
            title=data.get("title", "Ticket issu de conversation"),
            description=data.get("description", ""),
            category=data.get("category", "General"),
            priority=data.get("priority", "Medium"),
            summary=data.get("summary", ""),
        )

    async def create_ticket_from_suggestion(
        self,
        suggestion: TicketDraftSuggestion,
        user_email: str,
        user_name: Optional[str] = None,
        conversation_id: Optional[int] = None,
        ticket_type: int = 1,
    ) -> TicketResponse:
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
