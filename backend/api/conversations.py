from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db
from models.schemas import ConversationResponse, ConversationSummary
from services.conversation_service import ConversationService
from services import ollama_memory


router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if settings.OLLAMA_ONLY:
        return ollama_memory.list_conversations(limit)
    return await ConversationService(db).get_recent_conversations(limit)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    if settings.OLLAMA_ONLY:
        conversation = ollama_memory.get_conversation(conversation_id)
    else:
        conversation = await ConversationService(db).get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conversation
