import json
import logging
import hashlib
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, Request, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Optional

from db.database import get_db
from models.schemas import AttachmentResponse, ChatFeedbackCreate, ChatFeedbackResponse, ChatRequest
from core.ollama_provider import OllamaProvider
from core.groq_provider import GroqProvider
from core.gemini_provider import GeminiProvider
from core.fallback_provider import FallbackProvider
from core.classifier import Classifier
from rag.vector_store import VectorStore
from services.ticket_service import TicketService
from services.email_service import EmailService
from services.ollama_ticket_service import OllamaTicketService
from services.cache_service import CacheService
from services.conversation_service import ConversationService
from services.settings_service import SettingsService
from core.conversation_engine import ConversationEngine
from config import settings
from integrations.glpi_client import GLPIClient
from services import ollama_memory

logger = logging.getLogger(__name__)

# Safe JSON dumps that converts non-serializable objects (e.g., datetime) to strings
JSON_DUMPS = lambda obj: json.dumps(obj, default=str)

router = APIRouter(prefix="/chat", tags=["Chat"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "image/png", "image/jpeg", "image/webp", "application/pdf",
    "text/plain", "text/csv", "application/zip",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

base_providers = {}
glpi_client = GLPIClient() if settings.GLPI_ENABLED else None
try:
    base_providers["ollama"] = OllamaProvider()
except Exception as e:
    logger.error(f"Impossible d'initialiser OllamaProvider: {e}")

if settings.GROQ_API_KEY:
    try:
        base_providers["groq"] = GroqProvider()
    except Exception as e:
        logger.error(f"Impossible d'initialiser GroqProvider: {e}")

if settings.GEMINI_API_KEY:
    try:
        base_providers["gemini"] = GeminiProvider()
    except Exception as e:
        logger.error(f"Impossible d'initialiser GeminiProvider: {e}")

def build_llm_provider(priority: list[str] | None = None):
    active_priority = priority or settings.PROVIDER_PRIORITY
    providers = {name: provider for name, provider in base_providers.items() if name in active_priority}
    if not settings.ENABLE_FALLBACK or len(active_priority) == 1:
        return providers.get(active_priority[0], base_providers.get("ollama"))
    return FallbackProvider(providers, active_priority)

vector_store = VectorStore()
cache_service = CacheService()
llm_provider = build_llm_provider()
classifier = Classifier(llm_provider)


@router.post("/attachments", response_model=AttachmentResponse)
async def upload_attachment(file: UploadFile = File(...)):
    """Stocke une pièce jointe du chat avec une limite et des types contrôlés."""
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(status_code=415, detail="Type de fichier non pris en charge")

    data = await file.read(MAX_ATTACHMENT_SIZE + 1)
    if len(data) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=413, detail="La pièce jointe dépasse 10 Mo")

    attachment_id = uuid4().hex
    safe_name = Path(file.filename or "piece-jointe").name
    destination = UPLOAD_DIR / f"{attachment_id}_{safe_name}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return AttachmentResponse(
        id=attachment_id,
        name=safe_name,
        size=len(data),
        content_type=content_type,
        url=f"/chat/attachments/{attachment_id}",
    )


@router.get("/attachments/{attachment_id}")
async def download_attachment(attachment_id: str):
    matches = list(UPLOAD_DIR.glob(f"{attachment_id}_*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable")
    return FileResponse(matches[0])


@router.post("/feedback", response_model=ChatFeedbackResponse)
async def add_chat_feedback(
    payload: ChatFeedbackCreate,
    db: Optional[AsyncSession] = Depends(get_db),
):
    if settings.OLLAMA_ONLY:
        return ollama_memory.add_feedback(payload.model_dump())
    return await ConversationService(db).add_feedback(payload)

@router.post("")
async def chat_endpoint(
    request: Request, 
    chat_request: ChatRequest, 
    db: Optional[AsyncSession] = Depends(get_db)
):
    """
    Endpoint principal pour le chat. Renvoie une réponse SSE (Server-Sent Events).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Rate Limiting
    is_allowed = await cache_service.check_rate_limit(client_ip)
    if not is_allowed:
        raise HTTPException(status_code=429, detail="Too many requests")
    await cache_service.increment_rate_limit(client_ip)

    messages = [
        {"role": msg.role, "content": msg.content, "attachments": msg.attachments}
        for msg in chat_request.messages
    ]
    
    if not messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    user_message = messages[-1]["content"]
    current_attachments = messages[-1].get("attachments") or []
    if current_attachments:
        attachment_names = ", ".join(item.get("name", "fichier") for item in current_attachments)
        messages[-1]["content"] += f"\n\nPièces jointes disponibles : {attachment_names}"
    if not user_message.strip():
        raise HTTPException(status_code=400, detail="Le message utilisateur ne peut pas être vide")

    if settings.OLLAMA_ONLY:
        runtime_llm_provider = llm_provider
        runtime_priority = ["ollama"]
    else:
        settings_service = SettingsService(db)
        runtime_settings = await settings_service.get_settings()
        runtime_priority = runtime_settings.get("llm", {}).get("priority") or [
            runtime_settings.get("llm", {}).get("primary_provider", settings.PROVIDER_PRIORITY[0]),
            runtime_settings.get("llm", {}).get("fallback_1", settings.PROVIDER_PRIORITY[1] if len(settings.PROVIDER_PRIORITY) > 1 else "groq"),
            runtime_settings.get("llm", {}).get("fallback_2", settings.PROVIDER_PRIORITY[2] if len(settings.PROVIDER_PRIORITY) > 2 else "gemini"),
        ]
        runtime_llm_provider = build_llm_provider(runtime_priority)
    logger.info("[CHAT] Message reçu; providers actifs: %s", ", ".join(runtime_priority))
    runtime_classifier = Classifier(runtime_llm_provider)
    conversation_service = ConversationService(db) if db is not None else None

    conversation_id = chat_request.conversation_id
    if conversation_id is None and conversation_service is not None:
        conversation_id = await conversation_service.create_conversation(
            user_name=chat_request.user_name or "Utilisateur AUTOHALL",
            user_email=chat_request.user_email or "employe.fictif@autohall.ma",
        )
    elif conversation_id is None:
        conversation_id = ollama_memory.create_conversation(
            user_name=chat_request.user_name or "Utilisateur AUTOHALL",
            user_email=chat_request.user_email or "employe.fictif@autohall.ma",
        )
    
    # 2. Vérification du cache pour les questions fréquentes (seulement sur le premier message)
    if len(messages) == 1:
        msg_hash = hashlib.md5(user_message.encode()).hexdigest()
        cached_response = await cache_service.get_cached_response(msg_hash)
        
        if cached_response:
            logger.info("Réponse servie depuis le cache.")
            async def cache_stream():
                if conversation_service is not None:
                    await conversation_service.append_message(conversation_id, "user", user_message, {"attachments": current_attachments})
                else:
                    ollama_memory.append_conversation_message(conversation_id, "user", user_message, {"attachments": current_attachments})
                yield f"data: {JSON_DUMPS({'type': 'action', 'action': 'conversation_started', 'conversation_id': conversation_id})}\n\n"
                yield f"data: {JSON_DUMPS({'type': 'token', 'content': cached_response})}\n\n"
                yield f"data: {JSON_DUMPS({'type': 'done'})}\n\n"
                if conversation_service is not None:
                    await conversation_service.append_message(conversation_id, "assistant", cached_response, {"source": "cache"})
                else:
                    ollama_memory.append_conversation_message(conversation_id, "assistant", cached_response, {"source": "cache"})
            return StreamingResponse(cache_stream(), media_type="text/event-stream")

    # 3. Traitement via le moteur de conversation
    if settings.OLLAMA_ONLY or settings.GLPI_ENABLED:
        ticket_service = OllamaTicketService(glpi_client)
    else:
        ticket_service = TicketService(db)
    email_service = EmailService(db, runtime_llm_provider)
    
    engine = ConversationEngine(
        llm_provider=runtime_llm_provider,
        classifier=runtime_classifier,
        vector_store=vector_store,
        ticket_service=ticket_service,
        email_service=email_service
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        full_response = ""
        done_sent = False
        try:
            if conversation_service is not None:
                await conversation_service.append_message(conversation_id, "user", user_message, {"attachments": current_attachments})
            else:
                ollama_memory.append_conversation_message(conversation_id, "user", user_message, {"attachments": current_attachments})
            yield f"data: {JSON_DUMPS({'type': 'action', 'action': 'conversation_started', 'conversation_id': conversation_id})}\n\n"

            async for event in engine.process_message_stream(messages, user_email=chat_request.user_email or "employe.fictif@autohall.ma", user_name=chat_request.user_name, conversation_id=conversation_id):
                if event["type"] == "response_complete":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    done_sent = True
                    continue

                if event["type"] == "token":
                    full_response += event["content"]
                yield f"data: {JSON_DUMPS(event)}\n\n"

            if full_response:
                if conversation_service is not None:
                    await conversation_service.append_message(conversation_id, "assistant", full_response, {"source": "chatbot"})
                else:
                    ollama_memory.append_conversation_message(conversation_id, "assistant", full_response, {"source": "chatbot"})
            
            # Sauvegarder la réponse complète dans le cache si c'est un premier message
            if len(messages) == 1 and full_response:
                msg_hash = hashlib.md5(user_message.encode()).hexdigest()
                await cache_service.set_cached_response(msg_hash, full_response)
                
            if not done_sent:
                yield f"data: {JSON_DUMPS({'type': 'done'})}\n\n"
        except Exception as e:
            logger.exception("[CHAT] Échec du traitement du message")
            error_msg = (
                "Impossible de générer une réponse. Ollama est indisponible et "
                "les providers de secours ont également échoué. Vérifiez leur configuration."
            )
            yield f"data: {JSON_DUMPS({'type': 'error', 'message': error_msg})}\n\n"
            yield f"data: {JSON_DUMPS({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
