import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.chat import base_providers, build_llm_provider
from core.fallback_provider import FallbackProvider
from db.database import get_db
from models.schemas import ProviderTestResult, SettingsPayload
from services.settings_service import SettingsService
from config import settings as app_settings
from services import ollama_memory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


def _provider_status(provider_name: str) -> str:
    if provider_name == "ollama":
        return "Available" if "ollama" in base_providers else "Unavailable"
    return "Connected" if provider_name in base_providers else "Unavailable"


@router.get("", response_model=dict)
async def get_settings(db: AsyncSession = Depends(get_db)):
    if app_settings.OLLAMA_ONLY:
        stored = ollama_memory.get_settings()
        stored["providers"] = [
            {"name": "ollama", "label": "Ollama", "status": _provider_status("ollama"), "primary": True},
            {"name": "groq", "label": "Groq", "status": "Disabled", "fallback": False},
            {"name": "gemini", "label": "Gemini", "status": "Disabled", "fallback": False},
        ]
        return stored
    service = SettingsService(db)
    settings = await service.get_settings()
    llm = settings.get("llm", {})
    providers = [
        {
            "name": "ollama",
            "label": "Ollama",
            "status": _provider_status("ollama"),
            "primary": llm.get("primary_provider", "ollama") == "ollama",
        },
        {
            "name": "groq",
            "label": "Groq",
            "status": _provider_status("groq"),
            "fallback": llm.get("fallback_1", "groq") == "groq",
        },
        {
            "name": "gemini",
            "label": "Gemini",
            "status": _provider_status("gemini"),
            "fallback": llm.get("fallback_2", "gemini") == "gemini",
        },
    ]
    settings["providers"] = providers
    return settings


@router.put("", response_model=dict)
async def update_settings(payload: SettingsPayload, db: AsyncSession = Depends(get_db)):
    if app_settings.OLLAMA_ONLY:
        return ollama_memory.update_settings(payload.model_dump(exclude_unset=True))
    service = SettingsService(db)
    return await service.update_settings(payload.model_dump(exclude_unset=True))


@router.post("/providers/{provider_name}/test", response_model=ProviderTestResult)
async def test_provider(provider_name: str, db: AsyncSession = Depends(get_db)):
    if provider_name not in base_providers:
        raise HTTPException(status_code=404, detail="Provider non disponible")

    provider = base_providers[provider_name]
    started = time.perf_counter()
    try:
        await provider.chat([
            {"role": "user", "content": "Réponds uniquement par le mot OK."}
        ], temperature=0.0)
        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return ProviderTestResult(provider=provider_name, ok=True, message="Connexion réussie", latency_ms=latency_ms)
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return ProviderTestResult(provider=provider_name, ok=False, message=str(exc), latency_ms=latency_ms)
