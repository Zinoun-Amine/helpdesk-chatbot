from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class MessageRequest(BaseModel):
    role: str
    content: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)

class ChatRequest(BaseModel):
    messages: List[MessageRequest]
    conversation_id: Optional[int] = None
    temperature: float = 0.3
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class ChatFeedbackCreate(BaseModel):
    conversation_id: Optional[int] = None
    message_id: Optional[str] = None
    rating: int = Field(..., ge=-1, le=1)
    comment: Optional[str] = None


class ChatFeedbackResponse(BaseModel):
    id: int
    conversation_id: Optional[int] = None
    message_id: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime


class AttachmentResponse(BaseModel):
    id: str
    name: str
    size: int
    content_type: str
    url: str

class ChatResponse(BaseModel):
    message: str
    action: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    priority: str = Field(..., description="Low, Medium, High or Urgent")
    status: str = Field(default="Open", description="Open, In Progress, Waiting for User, Resolved, Closed")
    ticket_type: int = Field(default=1, description="1=Incident, 2=Demande")
    criticality: Optional[str] = None
    user_name: Optional[str] = None
    user_email: str
    conversation_id: Optional[int] = None
    summary: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_to_email: Optional[str] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_to_email: Optional[str] = None
    resolved_at: Optional[datetime] = None

class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    ticket_type: int = 1
    criticality: Optional[str] = None
    priority_value: Optional[int] = None
    user_name: Optional[str] = None
    user_email: str
    conversation_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_to_email: Optional[str] = None
    assigned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TechnicianResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: Optional[str] = None
    team: Optional[str] = None
    category_id: Optional[int] = None
    active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class TicketAssignmentRequest(BaseModel):
    technician_id: Optional[int] = None
    technician_email: Optional[str] = None
    technician_name: Optional[str] = None
    assigned_by: Optional[str] = None
    reason: Optional[str] = None


class TicketAssignmentResponse(BaseModel):
    id: int
    ticket_id: int
    technician_id: int
    assigned_by: Optional[str] = None
    reason: Optional[str] = None
    assigned_at: datetime

    class Config:
        from_attributes = True


class TicketStatus(BaseModel):
    id: int
    status: str
    updated_at: datetime
    resolved_at: Optional[datetime] = None


class TicketMessageCreate(BaseModel):
    sender_role: str = Field(default="user", description="user, agent, system")
    sender_name: Optional[str] = None
    content: str


class TicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_role: str
    sender_name: Optional[str] = None
    content: str
    created_at: datetime


class TicketHistoryResponse(BaseModel):
    id: int
    ticket_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[str] = None
    created_at: datetime


class TicketDetailResponse(TicketResponse):
    messages: List[TicketMessageResponse] = []
    history: List[TicketHistoryResponse] = []


class TicketDraftSuggestion(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    summary: str


class ConversationTicketDraftRequest(BaseModel):
    messages: List[MessageRequest]
    conversation_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None

class EmailDraftCreate(BaseModel):
    ticket_id: int
    recipient_email: str
    subject: str
    body: str

class EmailDraftUpdate(BaseModel):
    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

class EmailDraftResponse(BaseModel):
    id: int
    ticket_id: int
    recipient_email: str
    subject: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class KBSearchResult(BaseModel):
    id: str
    title: str
    category: str
    problem_description: str
    solution_steps: List[str]
    score: float

class MessageResponse(BaseModel):
    id: Optional[int] = None
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationResponse(BaseModel):
    conversation_id: int
    messages: List[MessageResponse]


class ConversationSummary(BaseModel):
    id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    status: str
    current_state: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ProviderStats(BaseModel):
    provider: str
    label: str
    requests: int
    successes: int
    errors: int
    fallbacks: int
    avg_response_ms: float = 0.0
    utilization: float = 0.0


class DashboardResponse(BaseModel):
    totals: Dict[str, Any]
    charts: Dict[str, Any]
    recent_conversations: List[ConversationSummary]
    llm_providers: List[ProviderStats]


class SettingsPayload(BaseModel):
    general: Dict[str, Any] = Field(default_factory=dict)
    appearance: Dict[str, Any] = Field(default_factory=dict)
    chat: Dict[str, Any] = Field(default_factory=dict)
    llm: Dict[str, Any] = Field(default_factory=dict)
    notifications: Dict[str, Any] = Field(default_factory=dict)


class ProviderTestResult(BaseModel):
    provider: str
    ok: bool
    message: str
    latency_ms: Optional[float] = None

class CategoryResponse(BaseModel):
    name: str
    description: Optional[str] = None
