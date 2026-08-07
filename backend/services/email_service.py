import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm_provider import LLMProvider
from integrations.smtp_client import SMTPClient, SMTPConfigurationError
from models.schemas import EmailDraftResponse, EmailDraftUpdate, TicketResponse

logger = logging.getLogger(__name__)

_memory_drafts: Dict[int, EmailDraftResponse] = {}
_next_memory_id = 1


class EmailService:
    """Génération, stockage et envoi réel des e-mails Helpdesk."""

    def __init__(self, db: Optional[AsyncSession], llm_provider: Optional[LLMProvider] = None):
        self.db = db
        self.llm = llm_provider
        self.smtp = SMTPClient()

    async def generate_draft_content(self, ticket: TicketResponse, conversation: List[Dict[str, str]]) -> str:
        if not self.llm:
            return f"Ticket ID: {ticket.id}\nCatégorie: {ticket.category}\nDescription: {ticket.description}\n\nMerci de traiter ce problème."

        prompt = (
            "Tu es un assistant Helpdesk. Rédige un email formel en français à l'équipe IT de niveau 2.\n"
            f"Le ticket #{ticket.id} a été créé. Catégorie: {ticket.category}, Criticité: {ticket.criticality}, Priorité: {ticket.priority}.\n"
            f"Description initiale: {ticket.description}\n"
            "Résume le problème en 3-4 lignes maximum. Ne mets pas d'objet, uniquement le corps."
        )
        try:
            return (await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.2)).strip()
        except Exception as exc:
            logger.error("Erreur de génération de l'e-mail via LLM: %s", exc)
            return f"Détails du ticket:\nID: {ticket.id}\nCatégorie: {ticket.category}\nProblème: {ticket.description}"

    async def create_draft(self, ticket_id: int, recipient_email: str, subject: str, body: str) -> EmailDraftResponse:
        global _next_memory_id
        if not recipient_email:
            raise SMTPConfigurationError(
                "Aucun destinataire: ticket.user_email ou SMTP_RECIPIENT est requis."
            )
        if self.db is None:
            now = datetime.now(timezone.utc)
            draft = EmailDraftResponse(
                id=_next_memory_id,
                ticket_id=ticket_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                status="draft",
                created_at=now,
                updated_at=now,
            )
            _memory_drafts[_next_memory_id] = draft
            _next_memory_id += 1
            return draft

        result = await self.db.execute(text("""
            INSERT INTO email_drafts (ticket_id, recipient_email, subject, body, status)
            VALUES (:ticket_id, :recipient_email, :subject, :body, 'draft')
            RETURNING id, ticket_id, recipient_email, subject, body, status, created_at, updated_at
        """), {"ticket_id": ticket_id, "recipient_email": recipient_email, "subject": subject, "body": body})
        row = result.fetchone()
        await self.db.commit()
        return EmailDraftResponse(**row._mapping)

    async def get_draft(self, draft_id: int) -> Optional[EmailDraftResponse]:
        if self.db is None:
            return _memory_drafts.get(draft_id)
        result = await self.db.execute(text("SELECT * FROM email_drafts WHERE id = :id"), {"id": draft_id})
        row = result.fetchone()
        return EmailDraftResponse(**row._mapping) if row else None

    async def update_draft(self, draft_id: int, updates: EmailDraftUpdate) -> Optional[EmailDraftResponse]:
        if self.db is None:
            current = _memory_drafts.get(draft_id)
            if not current or current.status != "draft":
                return None
            values = current.model_dump()
            values.update({key: value for key, value in updates.model_dump(exclude_unset=True).items() if value is not None})
            values["updated_at"] = datetime.now(timezone.utc)
            updated = EmailDraftResponse(**values)
            _memory_drafts[draft_id] = updated
            return updated

        update_fields = []
        params = {"id": draft_id}
        for field in ("recipient_email", "subject", "body"):
            value = getattr(updates, field)
            if value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value
        if not update_fields:
            return await self.get_draft(draft_id)
        result = await self.db.execute(text(f"""
            UPDATE email_drafts SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND status = 'draft'
            RETURNING id, ticket_id, recipient_email, subject, body, status, created_at, updated_at
        """), params)
        row = result.fetchone()
        await self.db.commit()
        return EmailDraftResponse(**row._mapping) if row else None

    async def send_draft(self, draft_id: int) -> Optional[EmailDraftResponse]:
        draft = await self.get_draft(draft_id)
        if not draft or draft.status != "draft":
            return None

        # L'envoi SMTP est effectué avant de marquer le brouillon comme envoyé.
        await self.smtp.send(draft.recipient_email, draft.subject, draft.body)
        if self.db is None:
            sent = draft.model_copy(update={"status": "sent", "updated_at": datetime.now(timezone.utc)})
            _memory_drafts[draft_id] = sent
            return sent

        result = await self.db.execute(text("""
            UPDATE email_drafts SET status = 'sent', updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND status = 'draft'
            RETURNING id, ticket_id, recipient_email, subject, body, status, created_at, updated_at
        """), {"id": draft_id})
        row = result.fetchone()
        await self.db.commit()
        return EmailDraftResponse(**row._mapping) if row else None
