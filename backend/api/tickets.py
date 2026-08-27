import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.schemas import (
    TicketCreate,
    TicketDetailResponse,
    TicketDraftSuggestion,
    TicketMessageCreate,
    TicketMessageResponse,
    TicketHistoryResponse,
    TicketResponse,
    TicketStatus,
    TicketUpdate,
    EmailDraftUpdate,
    EmailDraftResponse,
    ConversationTicketDraftRequest,
    TicketAssignmentRequest,
    TicketAssignmentResponse,
    TechnicianResponse,
)
from services.ticket_service import TicketService
from services.ollama_ticket_service import OllamaTicketService
from services.email_service import EmailService
from integrations.smtp_client import SMTPConfigurationError, SMTPDeliveryError
from services.settings_service import SettingsService
from api.chat import llm_provider, glpi_client
from config import settings
from services import ollama_memory
from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tickets"])


def _ollama_ticket_service() -> OllamaTicketService:
    return OllamaTicketService(glpi_client)

@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate, db: AsyncSession = Depends(get_db)):
    """Crée un ticket, puis son brouillon e-mail (et l'envoie si activé)."""
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        created_ticket = await _ollama_ticket_service().create_ticket(ticket.model_dump())
    else:
        created_ticket, _ = await TicketService(db).create_ticket(ticket.model_dump())

    email_service = EmailService(db)
    try:
        recipients = []
        if created_ticket.assigned_to_email:
            technician_body = await email_service.generate_technician_notification(created_ticket)
            recipients.append((
                created_ticket.assigned_to_email,
                f"[AUTOHALL Helpdesk] Ticket #{created_ticket.id} assigné — {created_ticket.category} / {created_ticket.priority}",
                technician_body,
            ))
        if created_ticket.user_email:
            user_body = await email_service.generate_draft_content(created_ticket, [])
            recipients.append((
                created_ticket.user_email,
                f"Confirmation de votre ticket #{created_ticket.id} — {created_ticket.category}",
                user_body,
            ))

        for recipient_email, subject, body in recipients:
            draft = await email_service.create_draft(
                ticket_id=created_ticket.id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
            )
            if settings.SMTP_AUTO_SEND:
                await email_service.send_draft(draft.id)
    except SMTPConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SMTPDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return created_ticket

@router.get("/tickets", response_model=List[TicketResponse])
async def list_tickets(
    user_email: Optional[str] = None,
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin":
        user_email = current_user["email"]

    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        return await _ollama_ticket_service().list_tickets(search=search, status=status, priority=priority)
    """Liste les tickets avec recherche et filtres."""
    service = TicketService(db)
    return await service.list_tickets(user_email=user_email, search=search, status=status, priority=priority)

@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        ticket = await _ollama_ticket_service().get_ticket_detail(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        return ticket
    service = TicketService(db)
    ticket = await service.get_ticket_detail(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket

@router.get("/tickets/{ticket_id}/status", response_model=TicketStatus)
async def get_ticket_status(ticket_id: int, db: AsyncSession = Depends(get_db)):
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        status = await _ollama_ticket_service().get_ticket_status(ticket_id)
        if not status:
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        return status
    """Récupère le statut d'un ticket spécifique."""
    service = TicketService(db)
    status = await service.get_ticket_status(ticket_id)
    if not status:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return status

@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: int, updates: TicketUpdate, db: AsyncSession = Depends(get_db)):
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        ticket = await _ollama_ticket_service().update_ticket(ticket_id, updates)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        return ticket
    """Met à jour un ticket."""
    service = TicketService(db)
    ticket = await service.update_ticket(ticket_id, updates)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket

@router.get("/tickets/{ticket_id}/messages", response_model=List[TicketMessageResponse])
async def get_ticket_messages(ticket_id: int, db: AsyncSession = Depends(get_db)):
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        service = _ollama_ticket_service()
        if settings.GLPI_ENABLED and not await service.get_ticket(ticket_id):
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        if not settings.GLPI_ENABLED and not ollama_memory.get_ticket(ticket_id):
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        return await service.get_ticket_messages(ticket_id)
    service = TicketService(db)
    return await service.get_ticket_messages(ticket_id)

@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessageResponse)
async def add_ticket_message(ticket_id: int, payload: TicketMessageCreate, db: AsyncSession = Depends(get_db)):
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        service = _ollama_ticket_service()
        if settings.GLPI_ENABLED and not await service.get_ticket(ticket_id):
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        message = await service.add_ticket_message(ticket_id, payload)
        if not message:
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        return message
    service = TicketService(db)
    message = await service.add_ticket_message(ticket_id, payload)
    if not message:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return message

@router.get("/tickets/{ticket_id}/history", response_model=List[TicketHistoryResponse])
async def get_ticket_history(ticket_id: int, db: AsyncSession = Depends(get_db)):
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        service = _ollama_ticket_service()
        if settings.GLPI_ENABLED and not await service.get_ticket(ticket_id):
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        if not settings.GLPI_ENABLED and not ollama_memory.get_ticket(ticket_id):
            raise HTTPException(status_code=404, detail="Ticket introuvable")
        return await service.get_ticket_history(ticket_id)
    service = TicketService(db)
    return await service.get_ticket_history(ticket_id)

@router.post("/tickets/from-conversation/draft", response_model=TicketDraftSuggestion)
async def draft_from_conversation(payload: ConversationTicketDraftRequest, db: AsyncSession = Depends(get_db)):
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Cette fonction requiert PostgreSQL. Désactivez OLLAMA_ONLY.",
        )

    service = TicketService(db)
    suggestion = await service.suggest_from_conversation(
        llm_provider,
        [{"role": message.role, "content": message.content} for message in payload.messages],
        user_name=payload.user_name,
        user_email=payload.user_email,
    )
    return suggestion

@router.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(ticket_id: int, payload: TicketAssignmentRequest, db: AsyncSession = Depends(get_db)):
    """Affecte un ticket à un technicien spécifique et garde une trace de l'assignation."""
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Réassignation manuelle non disponible en mode Ollama-only. Activez PostgreSQL.",
        )

    service = TicketService(db)
    ticket = await service.assign_ticket(
        ticket_id,
        technician_id=payload.technician_id,
        technician_email=payload.technician_email,
        technician_name=payload.technician_name,
        assigned_by=payload.assigned_by,
        reason=payload.reason,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket ou technicien introuvable")

    # Replace or create the pending draft so the frontend sends it to the
    # newly assigned technician, never to the previous draft recipient.
    email_service = EmailService(db, llm_provider)
    notification_body = await email_service.generate_technician_notification(ticket)
    notification_subject = (
        f"[AUTOHALL Helpdesk] Ticket #{ticket.id} assigné — "
        f"{ticket.category} / {ticket.priority}"
    )
    draft_result = await db.execute(
        text(
            """
            SELECT id, status
            FROM email_drafts
            WHERE ticket_id = :ticket_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"ticket_id": ticket.id},
    )
    latest_draft = draft_result.fetchone()
    if latest_draft and latest_draft._mapping["status"] == "draft":
        await email_service.update_draft(
            latest_draft._mapping["id"],
            EmailDraftUpdate(
                recipient_email=ticket.assigned_to_email,
                subject=notification_subject,
                body=notification_body,
            ),
        )
    else:
        await email_service.create_draft(
            ticket_id=ticket.id,
            recipient_email=ticket.assigned_to_email,
            subject=notification_subject,
            body=notification_body,
        )
    return ticket


@router.get("/technicians", response_model=List[TechnicianResponse])
async def list_technicians(db: AsyncSession = Depends(get_db)):
    """Liste les techniciens disponibles pour l'affectation des tickets."""
    # Fallback: mode Ollama-only ou GLPI (pas de DB) → lire depuis le dict statique
    if db is None:
        from services.ticket_service import TECHNICIAN_BY_CATEGORY
        return [
            TechnicianResponse(
                id=idx + 1,
                full_name=tech["name"],
                email=tech["email"],
                role=tech.get("role"),
                team=category,
                category_id=None,
                active=True,
                created_at=None,
            )
            for idx, (category, tech) in enumerate(TECHNICIAN_BY_CATEGORY.items())
        ]

    # Mode complet: lecture depuis la table technicians
    result = await db.execute(
        text(
            """
            SELECT id, full_name, email, role, team, category_id, active, created_at
            FROM technicians
            ORDER BY full_name ASC
            """
        )
    )
    rows = result.fetchall()
    return [TechnicianResponse(**row._mapping) for row in rows]


@router.get("/tickets/{ticket_id}/assignments", response_model=List[TicketAssignmentResponse])
async def get_ticket_assignments(ticket_id: int, db: AsyncSession = Depends(get_db)):
    """Renvoie l'historique des affectations d'un ticket."""
    if db is None:
        # Pas d'historique disponible sans PostgreSQL
        return []

    result = await db.execute(
        text(
            """
            SELECT id, ticket_id, technician_id, assigned_by, reason, assigned_at
            FROM ticket_assignments
            WHERE ticket_id = :ticket_id
            ORDER BY assigned_at DESC, id DESC
            """
        ),
        {"ticket_id": ticket_id},
    )
    rows = result.fetchall()
    return [TicketAssignmentResponse(**row._mapping) for row in rows]

@router.get("/tickets/{ticket_id}/email-draft", response_model=EmailDraftResponse)
async def get_ticket_email_draft(ticket_id: int, db: AsyncSession = Depends(get_db)):
    """Récupère le dernier brouillon d'email pour un ticket."""
    # Ollama-only / no DB: read in-memory drafts
    if db is None:
        try:
            from services import email_service as _email_service
            candidates = [d for d in _email_service._memory_drafts.values() if d.ticket_id == ticket_id]
            if not candidates:
                raise HTTPException(status_code=404, detail="Brouillon introuvable")
            draft = sorted(candidates, key=lambda d: d.created_at, reverse=True)[0]
            return draft
        except Exception:
            raise HTTPException(status_code=404, detail="Brouillon introuvable")

    # PostgreSQL mode: query latest draft for ticket
    result = await db.execute(
        text(
            """
            SELECT id, ticket_id, conversation_id, recipient_email, subject, body, status, created_at, sent_at
            FROM email_drafts
            WHERE ticket_id = :ticket_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"ticket_id": ticket_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Brouillon introuvable")
    return EmailDraftResponse(**row._mapping)

@router.put("/email-drafts/{draft_id}", response_model=EmailDraftResponse)
async def update_email_draft(draft_id: int, draft_update: EmailDraftUpdate, db: AsyncSession = Depends(get_db)):
    """Modifie le contenu d'un brouillon d'email avant envoi."""
    service = EmailService(db)
    draft = await service.update_draft(draft_id, draft_update)
    if not draft:
        raise HTTPException(status_code=404, detail="Brouillon introuvable ou déjà envoyé")
    return draft

@router.post("/email-drafts/{draft_id}/send", response_model=EmailDraftResponse)
async def send_email_draft(draft_id: int, db: AsyncSession = Depends(get_db)):
    """Envoie réellement le brouillon via SMTP."""
    service = EmailService(db)
    try:
        draft = await service.send_draft(draft_id)
    except SMTPConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SMTPDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not draft:
        raise HTTPException(status_code=404, detail="Brouillon introuvable ou déjà envoyé")
    return draft
