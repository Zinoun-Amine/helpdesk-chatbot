import asyncio
import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from core.llm_provider import LLMProvider
from core.classifier import Classifier
from rag.vector_store import VectorStore
from services.ticket_service import TicketService
from services.email_service import EmailService
from integrations.smtp_client import SMTPConfigurationError, SMTPDeliveryError
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
    "je souhaite créer un ticket",
    "je souhaite un ticket",
)

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
            greeting_prompt = (
                f"{self.system_prompt}\n"
                "L'utilisateur vient de saluer ou d'ouvrir la conversation avec une phrase courte. "
                "Réponds avec un accueil naturel, poli et bref, puis invite-le à décrire son problème informatique."
            )
            messages_for_llm = [{"role": "system", "content": greeting_prompt}] + messages
            async for chunk in self.llm.chat_stream(messages_for_llm):
                yield {"type": "token", "content": chunk}
            yield {"type": "response_complete"}
            return

        normalized = user_message.strip().lower()
        explicit_ticket_request = any(marker in normalized for marker in TICKET_REQUEST_MARKERS)

        if explicit_ticket_request:
            from models.schemas import TicketDraftSuggestion

            classification = await self.classifier.analyze_issue(user_message)
            category = classification.get("category") or "General"
            if category == "Inconnue":
                category = "Réseau" if any(word in normalized for word in ("wifi", "wifi", "wlan", "réseau", "connexion")) else "General"
            suggestion = TicketDraftSuggestion(
                title=(user_message[:80] or "Ticket AUTOHALL"),
                description=user_message,
                category=category,
                priority={1: "Urgent", 2: "High", 3: "Medium", 4: "Medium", 5: "Low", 6: "Low"}.get(classification.get("priority", 3), "Medium"),
                summary=user_message[:200],
            )
            ticket = await self.ticket_service.create_ticket_from_suggestion(
                suggestion,
                user_email=user_email,
                user_name=user_name,
                conversation_id=conversation_id,
                ticket_type=classification.get("type", 2),
            )
            yield {"type": "action", "action": "ticket_created", "ticket": ticket.model_dump()}
            yield {"type": "token", "content": f"Votre ticket a bien été créé sous le numéro #{ticket.id}. L’équipe support va traiter votre demande."}
            yield {"type": "response_complete"}
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
        
        # If it's an installation request, do not present KB solutions — create a ticket automatically.
        if force_create_for_install:
            kb_results = []

        if kb_results:
            # Informer le client qu'on a trouvé des infos KB
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

        # 3. Création de ticket (si pas de solution KB ou si l'utilisateur dit que la solution ne marche pas)
        # Note: Dans une vraie implémentation, on vérifierait si l'utilisateur a dit "non" à une solution précédente.
        # Ici on simplifie: si pas de RAG, on crée le ticket.
        
        try:
            suggestion = await self.ticket_service.suggest_from_conversation(
                self.llm,
                messages,
                user_name=user_name,
                user_email=user_email,
            )
        except Exception:
            logger.exception("Échec de la génération de la suggestion de ticket; utilisation du secours local")
            fallback_priority = "High" if classification.get("priority", 3) <= 2 else "Medium"
            suggestion = None
            from models.schemas import TicketDraftSuggestion

            suggestion = TicketDraftSuggestion(
                title=user_message[:80] or "Ticket AUTOHALL",
                description=user_message,
                category=classification.get("category", "General") or "General",
                priority=fallback_priority,
                summary=user_message[:200],
            )

        priority_label = {1: "Urgent", 2: "High", 3: "Medium", 4: "Medium", 5: "Low", 6: "Low"}.get(
            classification.get("priority", 3), "Medium"
        )
        suggestion = suggestion.model_copy(update={
            "category": classification.get("category") or suggestion.category,
            "priority": priority_label,
        })

        ticket = await self.ticket_service.create_ticket_from_suggestion(
            suggestion,
            user_email=user_email,
            user_name=user_name,
            conversation_id=conversation_id,
            ticket_type=classification.get("type", 1),
        )
        yield {"type": "action", "action": "ticket_created", "ticket": ticket.model_dump()}
        
        # 4. Réponse finale au client
        # For installation requests we avoid calling the LLM to generate the final message
        # because the model may produce irrelevant content. Instead use a deterministic reply.
        if force_create_for_install:
            assistant_msg = (
                f"Votre demande d'installation a été créée sous le ticket #{ticket.id}. "
                "L'équipe support s'en occupe et vous contactera si des informations supplémentaires sont nécessaires."
            )
            yield {"type": "token", "content": assistant_msg}
        else:
            final_prompt = (
                f"{self.system_prompt}\n"
                f"Tu as créé le ticket #{ticket.id} intitulé '{ticket.title}'. "
                "Informe poliment l'utilisateur que son ticket a été créé avec succès et que l'équipe IT s'en occupe."
            )
            messages_for_llm = [{"role": "system", "content": final_prompt}]
            async for chunk in self.llm.chat_stream(messages_for_llm):
                yield {"type": "token", "content": chunk}

        yield {"type": "response_complete"}

        # 5. Création du brouillon d'email, sans bloquer la réponse utilisateur
        try:
            email_content = await self.email_service.generate_draft_content(ticket, messages)
            draft = await self.email_service.create_draft(
                ticket_id=ticket.id,
                recipient_email=ticket.user_email or settings.SMTP_RECIPIENT,
                subject=f"Nouveau Ticket: {ticket.category} - {ticket.priority}",
                body=email_content,
            )
            if settings.SMTP_AUTO_SEND:
                draft = await self.email_service.send_draft(draft.id) or draft
            yield {"type": "action", "action": "email_draft", "draft": draft.model_dump()}
        except (SMTPConfigurationError, SMTPDeliveryError) as exc:
            logger.error("Le ticket %s a été créé, mais son e-mail n'a pas été envoyé: %s", ticket.id, exc)
            yield {"type": "action", "action": "email_error", "detail": str(exc)}
