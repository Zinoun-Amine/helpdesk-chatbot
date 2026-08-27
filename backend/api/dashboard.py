import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from core.fallback_provider import FallbackProvider
from api.chat import llm_provider
from services.dashboard_service import DashboardService
from models.schemas import DashboardResponse
from config import settings
from services import ollama_memory
from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    period: str = Query("30d", description="today, 7d, 30d, 90d ou custom"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if settings.OLLAMA_ONLY:
        return ollama_memory.get_dashboard()
    service = DashboardService(db, llm_provider if isinstance(llm_provider, FallbackProvider) else None)
    user_email = None if current_user.get("role") == "admin" else current_user["email"]
    return await service.get_dashboard(period=period, start=start, end=end, user_email=user_email)
