"""Mémoire locale utilisée quand le projet fonctionne en mode Ollama seul.

Elle permet aux écrans Tickets/Dashboard/Settings de rester utilisables sans
PostgreSQL. Les données sont conservées uniquement pendant la vie du backend.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.schemas import (
    ConversationSummary,
    ChatFeedbackResponse,
    DashboardResponse,
    MessageResponse,
    ProviderStats,
    TicketDetailResponse,
    TicketMessageResponse,
    TicketResponse,
    TicketStatus,
)
from services.settings_service import DEFAULT_SETTINGS
from services.ticket_service import TECHNICIAN_BY_CATEGORY


_tickets: Dict[int, TicketResponse] = {}
_ticket_messages: Dict[int, List[TicketMessageResponse]] = {}
_next_ticket_id = 1
_conversations: Dict[int, ConversationSummary] = {}
_conversation_messages: Dict[int, List[MessageResponse]] = {}
_next_conversation_id = 1
_feedback: List[ChatFeedbackResponse] = []
_next_feedback_id = 1
_settings = deepcopy(DEFAULT_SETTINGS)
_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "ollama_memory.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _save_state() -> None:
    """Persiste la mémoire Ollama pour survivre au redémarrage du backend."""
    payload = {
        "next_ticket_id": _next_ticket_id,
        "next_conversation_id": _next_conversation_id,
        "next_feedback_id": _next_feedback_id,
        "tickets": [ticket.model_dump(mode="json") for ticket in _tickets.values()],
        "ticket_messages": {
            str(ticket_id): [message.model_dump(mode="json") for message in messages]
            for ticket_id, messages in _ticket_messages.items()
        },
        "conversations": [conversation.model_dump(mode="json") for conversation in _conversations.values()],
        "conversation_messages": {
            str(conversation_id): [message.model_dump(mode="json") for message in messages]
            for conversation_id, messages in _conversation_messages.items()
        },
        "feedback": [feedback.model_dump(mode="json") for feedback in _feedback],
        "settings": _settings,
    }
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = _STATE_FILE.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_file.replace(_STATE_FILE)


def _load_state() -> None:
    global _next_ticket_id, _next_conversation_id, _next_feedback_id, _settings
    if not _STATE_FILE.exists():
        return
    try:
        payload = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        _next_ticket_id = int(payload.get("next_ticket_id", 1))
        _next_conversation_id = int(payload.get("next_conversation_id", 1))
        _next_feedback_id = int(payload.get("next_feedback_id", 1))
        _tickets.update({
            ticket.id: ticket
            for ticket in (TicketResponse.model_validate(item) for item in payload.get("tickets", []))
        })
        _ticket_messages.update({
            int(ticket_id): [TicketMessageResponse.model_validate(item) for item in messages]
            for ticket_id, messages in payload.get("ticket_messages", {}).items()
        })
        _conversations.update({
            conversation.id: conversation
            for conversation in (ConversationSummary.model_validate(item) for item in payload.get("conversations", []))
        })
        _conversation_messages.update({
            int(conversation_id): [MessageResponse.model_validate(item) for item in messages]
            for conversation_id, messages in payload.get("conversation_messages", {}).items()
        })
        _feedback.extend(ChatFeedbackResponse.model_validate(item) for item in payload.get("feedback", []))
        if isinstance(payload.get("settings"), dict):
            _settings = payload["settings"]
    except (OSError, ValueError, TypeError) as exc:
        # Une sauvegarde corrompue ne doit pas empêcher Ollama de démarrer.
        print(f"Impossible de charger la mémoire Ollama persistée: {exc}")


_load_state()


def create_conversation(user_name: Optional[str] = None, user_email: Optional[str] = None) -> int:
    global _next_conversation_id
    conversation_id = _next_conversation_id
    _next_conversation_id += 1
    now = _now()
    _conversations[conversation_id] = ConversationSummary(
        id=conversation_id,
        user_name=user_name,
        user_email=user_email,
        status="active",
        current_state="accueil",
        created_at=now,
        updated_at=now,
        message_count=0,
    )
    _conversation_messages[conversation_id] = []
    _save_state()
    return conversation_id


def append_conversation_message(
    conversation_id: int,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    conversation = _conversations.get(conversation_id)
    if not conversation:
        return
    messages = _conversation_messages.setdefault(conversation_id, [])
    messages.append(MessageResponse(
        id=len(messages) + 1,
        role=role,
        content=content,
        timestamp=_now(),
        metadata=metadata or {},
    ))
    values = conversation.model_dump()
    values["updated_at"] = _now()
    values["message_count"] = len(messages)
    _conversations[conversation_id] = ConversationSummary(**values)
    _save_state()


def list_conversations(limit: int = 50) -> List[ConversationSummary]:
    return sorted(_conversations.values(), key=lambda item: item.updated_at, reverse=True)[:limit]


def get_conversation(conversation_id: int) -> Optional[Dict[str, Any]]:
    if conversation_id not in _conversations:
        return None
    return {
        "conversation_id": conversation_id,
        "messages": deepcopy(_conversation_messages.get(conversation_id, [])),
    }


def add_feedback(payload: Dict[str, Any]) -> ChatFeedbackResponse:
    global _next_feedback_id
    feedback = ChatFeedbackResponse(
        id=_next_feedback_id,
        conversation_id=payload.get("conversation_id"),
        message_id=payload.get("message_id"),
        rating=payload["rating"],
        comment=payload.get("comment"),
        created_at=_now(),
    )
    _next_feedback_id += 1
    _feedback.append(feedback)
    _save_state()
    return feedback


def list_tickets(
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> List[TicketResponse]:
    result = list(_tickets.values())
    if isinstance(search, str) and search:
        needle = search.lower()
        result = [ticket for ticket in result if needle in f"{ticket.title} {ticket.description} {ticket.category}".lower()]
    if isinstance(status, str) and status:
        result = [ticket for ticket in result if ticket.status == status]
    if isinstance(priority, str) and priority:
        result = [ticket for ticket in result if ticket.priority == priority]
    return sorted(result, key=lambda ticket: ticket.created_at, reverse=True)


def create_ticket(data: Dict[str, Any], ticket_id: Optional[int] = None) -> TicketResponse:
    global _next_ticket_id
    now = _now()
    category = data.get("category")
    technician = None
    if category:
        for known_category, tech in TECHNICIAN_BY_CATEGORY.items():
            if known_category.lower() == str(category).strip().lower():
                technician = tech
                break

    assigned_id = ticket_id or _next_ticket_id
    ticket = TicketResponse(
        id=assigned_id,
        title=data["title"],
        description=data["description"],
        category=category,
        priority=data["priority"],
        status=data.get("status", "Open"),
        ticket_type=data.get("ticket_type", 1),
        criticality=data.get("criticality"),
        priority_value=None,
        user_name=data.get("user_name"),
        user_email=data["user_email"],
        conversation_id=data.get("conversation_id"),
        assigned_to_id=data.get("assigned_to_id"),
        assigned_to_name=data.get("assigned_to_name") or (technician["name"] if technician else None),
        assigned_to_email=data.get("assigned_to_email") or (technician["email"] if technician else None),
        assigned_at=now if (data.get("assigned_to_email") or (technician and technician.get("email"))) else None,
        created_at=now,
        updated_at=now,
        resolved_at=None,
    )
    _tickets[assigned_id] = ticket
    _ticket_messages.setdefault(assigned_id, [])
    _next_ticket_id = max(_next_ticket_id, assigned_id + 1)
    _save_state()
    return ticket


def get_ticket(ticket_id: int) -> Optional[TicketResponse]:
    return _tickets.get(ticket_id)


def get_ticket_detail(ticket_id: int) -> Optional[TicketDetailResponse]:
    ticket = get_ticket(ticket_id)
    if not ticket:
        return None
    return TicketDetailResponse(
        **ticket.model_dump(),
        messages=_ticket_messages.get(ticket_id, []),
        history=[],
    )


def update_ticket(ticket_id: int, updates: Dict[str, Any]) -> Optional[TicketResponse]:
    ticket = get_ticket(ticket_id)
    if not ticket:
        return None
    values = ticket.model_dump()
    values.update({key: value for key, value in updates.items() if value is not None})
    values["updated_at"] = _now()
    updated = TicketResponse(**values)
    _tickets[ticket_id] = updated
    _save_state()
    return updated


def get_ticket_status(ticket_id: int) -> Optional[TicketStatus]:
    ticket = get_ticket(ticket_id)
    if not ticket:
        return None
    return TicketStatus(id=ticket.id, status=ticket.status, updated_at=ticket.updated_at, resolved_at=ticket.resolved_at)


def get_ticket_messages(ticket_id: int) -> List[TicketMessageResponse]:
    return _ticket_messages.get(ticket_id, [])


def add_ticket_message(ticket_id: int, data: Dict[str, Any]) -> Optional[TicketMessageResponse]:
    if not get_ticket(ticket_id):
        return None
    messages = _ticket_messages.setdefault(ticket_id, [])
    message = TicketMessageResponse(
        id=len(messages) + 1,
        ticket_id=ticket_id,
        sender_role=data.get("sender_role", "user"),
        sender_name=data.get("sender_name"),
        content=data["content"],
        created_at=_now(),
    )
    messages.append(message)
    _save_state()
    return message


def get_settings() -> Dict[str, Any]:
    return deepcopy(_settings)


def update_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(_settings.get(key), dict):
            _settings[key].update(value)
    else:
        _settings[key] = value
    _save_state()
    return get_settings()


def get_dashboard() -> DashboardResponse:
    tickets = list(_tickets.values())
    provider = ProviderStats(
        provider="ollama",
        label="Ollama",
        requests=0,
        successes=0,
        errors=0,
        fallbacks=0,
        avg_response_ms=0.0,
        utilization=100.0,
    )
    return DashboardResponse(
        totals={"tickets": len(tickets), "conversations": len(_conversations), "active_users": len({item.user_email for item in _conversations.values() if item.user_email})},
        charts={"activity": [], "ticket_activity": [], "ticket_status": [], "ticket_priority": []},
        recent_conversations=list_conversations(8),
        llm_providers=[provider],
    )
