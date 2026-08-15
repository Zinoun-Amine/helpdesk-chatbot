import asyncio
import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

from core.llm_provider import LLMProvider
from core.classifier import Classifier
from rag.vector_store import VectorStore
from services.ticket_service import TicketService, TECHNICIAN_BY_CATEGORY
from services.email_service import EmailService
from db.database import AsyncSessionLocal
from config import settings

logger = logging.getLogger(__name__)

GREETING_MARKERS = (
    "bonjour",
    "salut",
    "hello",
    "bonsoir",
    "coucou",
    "merci",
    "salam",
)

INSTALL_MARKERS = (
    "installer",
    "installation",
    "je souhaite installer",
    "je veux installer",
    "demande d'installation",
    "installer le",
)

TICKET_REQUEST_MARKERS = (
    "créer un ticket",
    "creer un ticket",
    "nouveau ticket",
    "ouvrir un ticket",
    "ticket support",
    "create ticket",
    "new ticket",
    "je veux un ticket",
    "contacter le support",
    "je veux contacter le support",
    "je souhaite créer un ticket",
    "je souhaite un ticket",
)


def _build_tech_confirmation(ticket_id: int, category: Optional[str], assigned_to_name: Optional[str]) -> str:
    """
    Retourne une phrase de confirmation mentionnant le technicien assigné.
    Utilisé pour les messages déterministes (sans LLM).
    """
    tech_name = assigned_to_name
    tech_role = None
    if category:
        tech_info = TECHNICIAN_BY_CATEGORY.get(category)
        if tech_info:
            tech_role = tech_info.get("role")

    if tech_name and tech_role:
        return (
            f"Votre ticket **#{ticket_id}** a été créé et assigné à **{tech_name}** "
            f"({tech_role}). Vous serez recontacté(e) sous 24h."
        )
    elif tech_name:
        return (
            f"Votre ticket **#{ticket_id}** a été créé et assigné à **{tech_name}**. "
            f"Vous serez recontacté(e) sous 24h."
        )
    else:
        return (
            f"Votre ticket **#{ticket_id}** a été créé. "
            f"L'équipe support va traiter votre demande."
        )


def _build_tech_line(category: Optional[str], assigned_to_name: Optional[str]) -> str:
    """
    Retourne la partie 'assigné à X (rôle)' pour injection dans un prompt LLM.
    """
    tech_name = assigned_to_name
    tech_role = None
    if category:
        tech_info = TECHNICIAN_BY_CATEGORY.get(category)
        if tech_info:
            tech_role = tech_info.get("role")

    if tech_name and tech_role:
        return f"assigné à **{tech_name}** ({tech_role}), vous serez recontacté(e) sous 24h"
    elif tech_name:
        return f"assigné à **{tech_name}**, vous serez recontacté(e) sous 24h"
    else:
        return "pris en charge par l'équipe support"


class ConversationEngine:
    """
    Machine à états pour le flux conversationnel du chatbot Helpdesk.
    États possibles (implicites):
    - ACCUEIL
    - COLLECTE_INFO
    - QUALIFICATION & CLASSIFICATION
    - RECHERCHE_KB
    - CREATION_TICKET
    - EMAIL_DRAFT
    - CONSULTATION
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        classifier: Classifier,
        vector_store: VectorStore,
        ticket_service: TicketService,
        email_service: EmailService
    ):
        self.llm = llm_provider
        self.classifier = classifier
        self.vector_store = vector_store
        self.ticket_service = ticket_service
        self.email_service = email_service

        self.system_prompt = (
            "Tu es l'assistant Helpdesk virtuel pour AUTOHALL (concessionnaire automobile). "
            "Ton rôle est d'aider les employés avec leurs problèmes informatiques. "
            "Réponds toujours en FRANÇAIS, de manière professionnelle et concise. "
            "Ne demande JAMAIS de vraies données personnelles (utilise des données fictives si besoin). "
            "Si un problème est ambigu, pose une question de clarification pour bien comprendre de quoi il s'agit avant d'essayer de résoudre."
        )

    async def _handle_email_notifications_async(
        self,
        ticket_id: int,
        user_email: str,
        messages: List[Dict[str, str]],
        conversation_id: Optional[int]
    ):
        """
        Tâche de fond pour envoyer les emails de notification au technicien
        et créer le brouillon utilisateur.
        Utilise sa propre session de base de données.
        """
        try:
            async with AsyncSessionLocal() as db:
                ticket_service = TicketService(db)
                email_service = EmailService(db)

                ticket = await ticket_service.get_ticket(ticket_id)
                if not ticket:
                    logger.error("Ticket %s non trouvé pour les notifications email", ticket_id)
                    return

                # Notification au technicien
                sent = await email_service.notify_technician(ticket)
                if sent:
                    logger.info("[NOTIF] Email technicien envoyé pour ticket #%s → %s",
                                ticket.id, ticket.assigned_to_email)
                else:
                    logger.info("[NOTIF] Email technicien non envoyé pour ticket #%s (SMTP désactivé ou pas de technicien).",
                                ticket.id)

                # Création du brouillon utilisateur (et envoi si auto-send)
                try:
                    email_content = await email_service.generate_draft_content(ticket, messages)
                    draft = await email_service.create_draft(
                        ticket_id=ticket.id,
                        recipient_email=ticket.user_email or settings.SMTP_RECIPIENT,
                        subject=f"Nouveau Ticket: {ticket.category} - {ticket.priority}",
                        body=email_content,
                    )
                    if settings.SMTP_AUTO_SEND:
                        draft = await email_service.send_draft(draft.id) or draft
                except Exception as e:
                    logger.error("Erreur lors de la création/envoi du draft pour ticket %s: %s", ticket.id, e)
        except Exception as e:
            logger.error("Erreur dans la tâche de notification email pour ticket %s: %s", ticket_id, e)

    async def process_message_stream(
        self,
        messages: List[Dict[str, str]],
        user_email: str = "employe.fictif@autohall.ma",
        conversation_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Traite le flux de conversation et retourne un générateur d'événements.
        Les événements peuvent être des chunks de texte, ou des actions (ticket_created, etc.)
        """
        user_message = messages[-1]["content"]
        if conversation_id is not None:
            yield {"type": "action", "action": "conversation_context", "conversation_id": conversation_id}

        normalized_message = user_message.strip().lower()
        greeting_only = (
            normalized_message
            and len(normalized_message) <= 20
            and any(
                normalized_message == marker
                or normalized_message.startswith(f"{marker} ")
                or normalized_message.startswith(f"{marker}!")
                or normalized_message.startswith(f"{marker}?")
                for marker in GREETING_MARKERS
            )
        )
        if greeting_only:
            yield {"type": "token", "content": "Bonjour ! Décrivez votre problème informatique et je vous aiderai à le qualifier rapidement."}
            yield {"type": "response_complete"}
            return

        normalized = user_message.strip().lower()
        explicit_ticket_request = any(marker in normalized for marker in TICKET_REQUEST_MARKERS)

        if explicit_ticket_request:
            from models.schemas import TicketDraftSuggestion

            # Use the full conversation to generate a proper ticket suggestion
            suggestion = await self.ticket_service.suggest_from_conversation(
                self.llm,
                messages,  # <-- full conversation, not just the last message
                user_name=user_name,
                user_email=user_email,
            )
            # If category is still missing, fallback to classification
            if suggestion.category == "General":
                full_context = " ".join(m["content"] for m in messages if m.get("role") == "user")
                classification = await self.classifier.analyze_issue(full_context)
                category = classification.get("category") or "General"
                if category != "Inconnue":
                    suggestion = suggestion.model_copy(update={"category": category})

            ticket, created = await self.ticket_service.create_ticket_from_suggestion(
                suggestion,
                user_email=user_email,
                user_name=user_name,
                conversation_id=conversation_id,
                ticket_type=2,  # Type 2 = Service Request (explicit)
            )
            yield {"type": "action", "action": "ticket_created", "ticket": ticket.model_dump()}
            yield {
                "type": "token",
                "content": _build_tech_confirmation(ticket.id, ticket.category, ticket.assigned_to_name),
            }
            yield {"type": "response_complete"}

            if created:
                asyncio.create_task(self._handle_email_notifications_async(
                    ticket.id,
                    user_email,
                    messages,
                    conversation_id
                ))
            return

        classification_task = asyncio.create_task(self.classifier.analyze_issue(user_message))
        kb_task = asyncio.create_task(
            self.vector_store.search(
                query=user_message,
                top_k=3
            )
        )

        # 1. Classification du message
        classification = await classification_task
        yield {
            "type": "action",
            "action": "qualification",
            "qualification": {
                "type": classification.get("type", 1),
                "category": classification.get("category", "Inconnue"),
                "priority": classification.get("priority", 3),
                "criticality": classification.get("criticality", "moyenne"),
                "confidence": classification.get("confidence", 0.0),
            },
        }

        # Si la demande nécessite clarification
        if classification.get("needs_clarification", False):
            kb_task.cancel()
            clarification_prompt = (
                f"{self.system_prompt}\n"
                "Le dernier message de l'utilisateur n'est pas assez clair pour classifier le problème. "
                "Pose-lui une question courte et polie pour obtenir plus de détails (ex: logiciel concerné, message d'erreur, etc.)."
            )
            messages_for_llm = [{"role": "system", "content": clarification_prompt}] + messages
            async for chunk in self.llm.chat_stream(messages_for_llm):
                yield {"type": "token", "content": chunk}
            return

        # Detect explicit installation requests and force ticket creation
        normalized = user_message.strip().lower()
        force_create_for_install = classification.get("type", 1) == 2 or any(marker in normalized for marker in INSTALL_MARKERS)

        # 2. Recherche dans la base de connaissances (RAG)
        kb_results = await kb_task
        category = classification.get("category")
        if category and category != "Inconnue" and kb_results:
            filtered_results = [result for result in kb_results if result.category == category]
            if filtered_results:
                kb_results = filtered_results

        if force_create_for_install:
            kb_results = []

        if kb_results:
            yield {"type": "action", "action": "kb_result", "results": [res.model_dump() for res in kb_results]}

            context = "\n\n".join([
                f"Titre: {res.title}\nProblème: {res.problem_description}\nSolutions: {', '.join(res.solution_steps)}"
                for res in kb_results
            ])

            rag_prompt = (
                f"{self.system_prompt}\n"
                f"L'utilisateur a le problème suivant et a été classifié en '{classification.get('category')}'.\n"
                f"Voici des solutions possibles de la base de connaissances:\n{context}\n\n"
                "Propose ces solutions à l'utilisateur de manière naturelle. Demande-lui si cela résout son problème."
            )

            messages_for_llm = [{"role": "system", "content": rag_prompt}] + messages
            async for chunk in self.llm.chat_stream(messages_for_llm):
                yield {"type": "token", "content": chunk}
            return

        # 3. Création de ticket (si pas de solution KB)
        try:
            # Use full conversation to generate suggestion
            suggestion = await self.ticket_service.suggest_from_conversation(
                self.llm,
                messages,
                user_name=user_name,
                user_email=user_email,
            )
        except Exception:
            logger.exception("Échec de la génération de la suggestion de ticket; utilisation du secours local")
            from models.schemas import TicketDraftSuggestion
            fallback_priority = "High" if classification.get("priority", 3) <= 2 else "Medium"
            # Fallback uses the full conversation's last user message? Better to use full context but we'll keep last for brevity.
            # We'll use the entire conversation transcript to get context.
            full_context = " ".join(m["content"] for m in messages if m.get("role") == "user")
            suggestion = TicketDraftSuggestion(
                title=full_context[:80] or "Ticket AUTOHALL",
                description=full_context[:300] if full_context else "",
                category=classification.get("category", "General") or "General",
                priority=fallback_priority,
                summary=full_context[:200] if full_context else "",
            )

        priority_label = {1: "Urgent", 2: "High", 3: "Medium", 4: "Medium", 5: "Low", 6: "Low"}.get(
            classification.get("priority", 3), "Medium"
        )
        suggestion = suggestion.model_copy(update={
            "category": classification.get("category") or suggestion.category,
            "priority": priority_label,
        })

        ticket, created = await self.ticket_service.create_ticket_from_suggestion(
            suggestion,
            user_email=user_email,
            user_name=user_name,
            conversation_id=conversation_id,
            ticket_type=classification.get("type", 1),
        )
        yield {"type": "action", "action": "ticket_created", "ticket": ticket.model_dump()}

        # 4. Réponse finale au client avec mention du technicien assigné
        tech_line = _build_tech_line(ticket.category, ticket.assigned_to_name)

        if force_create_for_install:
            assistant_msg = (
                f"Votre demande d'installation a été créée sous le ticket **#{ticket.id}** "
                f"et {tech_line}."
            )
            yield {"type": "token", "content": assistant_msg}
        else:
            final_prompt = (
                f"{self.system_prompt}\n"
                f"Tu as créé le ticket #{ticket.id} intitulé '{ticket.title}', {tech_line}. "
                "Informe poliment l'utilisateur en mentionnant exactement : le numéro de ticket, "
                "le nom du technicien assigné et le délai de recontact de 24h. Sois concis, 2-3 phrases maximum."
            )
            messages_for_llm = [{"role": "system", "content": final_prompt}]
            async for chunk in self.llm.chat_stream(messages_for_llm):
                yield {"type": "token", "content": chunk}

        yield {"type": "response_complete"}

        # 5. Lancer les notifications en arrière-plan (seulement si nouveau ticket)
        if created:
            asyncio.create_task(self._handle_email_notifications_async(
                ticket.id,
                user_email,
                messages,
                conversation_id
            ))