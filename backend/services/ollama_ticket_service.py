"""Service ticket sans PostgreSQL, avec synchronisation GLPI optionnelle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.llm_provider import LLMProvider
from integrations.glpi_client import GLPIClient
from models.schemas import TicketDetailResponse, TicketDraftSuggestion, TicketResponse, TicketStatus, TicketUpdate
from services import ollama_memory
from services.ticket_service import PRIORITY_TO_CRITICALITY


class OllamaTicketService:
    def __init__(self, glpi_client: Optional[GLPIClient] = None):
        self.glpi = glpi_client

    @staticmethod
    def _glpi_to_ticket(data: Dict[str, Any]) -> TicketResponse:
        urgency = int(data.get("urgency", 3) or 3)
        priority = {5: "Urgent", 4: "High", 3: "Medium", 2: "Low", 1: "Low"}.get(urgency, "Medium")
        status = {1: "Open", 2: "Open", 3: "In Progress", 4: "Waiting for User", 5: "Resolved", 6: "Closed"}.get(data.get("status"), "Open")
        now = datetime.now(timezone.utc)
        return TicketResponse(
            id=int(data["id"]),
            title=data.get("name", data.get("title", "Ticket GLPI")),
            description=data.get("content", data.get("description", "")),
            category=str(data.get("itilcategories_id", data.get("category", "General"))),
            priority=priority,
            status=status,
            ticket_type=int(data.get("type", 1) or 1),
            criticality=PRIORITY_TO_CRITICALITY[priority.lower()],
            priority_value=urgency,
            user_name=None,
            user_email="",
            conversation_id=None,
            created_at=now,
            updated_at=now,
            resolved_at=None,
        )

    async def create_ticket(self, data: Dict[str, Any]) -> TicketResponse:
        if self.glpi:
            glpi_data = await self.glpi.create_ticket(data)
            ticket = self._glpi_to_ticket(glpi_data)
            merged = ticket.model_dump()
            merged.update(data)
            return ollama_memory.create_ticket(merged, ticket_id=ticket.id)
        return ollama_memory.create_ticket(data)

    async def list_tickets(self, search: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None) -> List[TicketResponse]:
        if not self.glpi:
            return ollama_memory.list_tickets(search, status, priority)
        result = [self._glpi_to_ticket(item) for item in await self.glpi.list_tickets()]
        if search:
            needle = search.lower()
            result = [ticket for ticket in result if needle in f"{ticket.title} {ticket.description}".lower()]
        if status:
            result = [ticket for ticket in result if ticket.status == status]
        if priority:
            result = [ticket for ticket in result if ticket.priority == priority]
        return result

    async def get_ticket(self, ticket_id: int) -> Optional[TicketResponse]:
        if self.glpi:
            try:
                return self._glpi_to_ticket(await self.glpi.get_ticket(ticket_id))
            except Exception:
                return ollama_memory.get_ticket(ticket_id)
        return ollama_memory.get_ticket(ticket_id)

    async def get_ticket_detail(self, ticket_id: int) -> Optional[TicketDetailResponse]:
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        local = ollama_memory.get_ticket_detail(ticket_id)
        return TicketDetailResponse(**ticket.model_dump(), messages=local.messages if local else [], history=local.history if local else [])

    async def get_ticket_status(self, ticket_id: int) -> Optional[TicketStatus]:
        ticket = await self.get_ticket(ticket_id)
        return TicketStatus(id=ticket.id, status=ticket.status, updated_at=ticket.updated_at, resolved_at=ticket.resolved_at) if ticket else None

    async def update_ticket(self, ticket_id: int, updates: TicketUpdate) -> Optional[TicketResponse]:
        values = updates.model_dump(exclude_unset=True)
        current = await self.get_ticket(ticket_id)
        if not current:
            return None
        if self.glpi:
            glpi_data = await self.glpi.update_ticket(ticket_id, values)
            updated = self._glpi_to_ticket(glpi_data)
            return ollama_memory.update_ticket(ticket_id, updated.model_dump()) or updated
        return ollama_memory.update_ticket(ticket_id, values)

    async def get_ticket_messages(self, ticket_id: int):
        return ollama_memory.get_ticket_messages(ticket_id)

    async def add_ticket_message(self, ticket_id: int, payload):
        if self.glpi and not ollama_memory.get_ticket(ticket_id):
            ticket = await self.get_ticket(ticket_id)
            if ticket:
                ollama_memory.create_ticket(ticket.model_dump(), ticket_id=ticket.id)
        return ollama_memory.add_ticket_message(ticket_id, payload.model_dump())

    async def get_ticket_history(self, ticket_id: int):
        detail = ollama_memory.get_ticket_detail(ticket_id)
        return detail.history if detail else []

    async def suggest_from_conversation(self, llm: LLMProvider, conversation_messages: List[Dict[str, str]], user_name: Optional[str] = None, user_email: Optional[str] = None) -> TicketDraftSuggestion:
        from services.ticket_service import TicketService
        return await TicketService(None).suggest_from_conversation(llm, conversation_messages, user_name, user_email)

    async def create_ticket_from_suggestion(self, suggestion: TicketDraftSuggestion, user_email: str, user_name: Optional[str] = None, conversation_id: Optional[int] = None, ticket_type: int = 1) -> TicketResponse:
        return await self.create_ticket({
            "title": suggestion.title,
            "description": suggestion.description,
            "category": suggestion.category,
            "priority": suggestion.priority,
            "status": "Open",
            "ticket_type": ticket_type,
            "criticality": PRIORITY_TO_CRITICALITY.get(suggestion.priority.lower(), "moyenne"),
            "user_name": user_name,
            "user_email": user_email,
            "conversation_id": conversation_id,
            "summary": suggestion.summary,
        })
