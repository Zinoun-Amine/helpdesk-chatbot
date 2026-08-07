from copy import deepcopy
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


DEFAULT_SETTINGS: Dict[str, Any] = {
    "general": {"chatbot_name": "AUTOHALL Helpdesk", "language": "fr"},
    "appearance": {"theme": "system"},
    "chat": {"temperature": 0.3, "max_tokens": 2048, "streaming": True, "memory": True, "history": True, "sources": True},
    "llm": {"primary_provider": "ollama", "fallback_1": "groq", "fallback_2": "gemini", "enable_fallback": True},
    "notifications": {"tickets": True, "status_changes": True, "errors": True, "system_events": True},
}


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self) -> Dict[str, Any]:
        result = await self.db.execute(text("SELECT data FROM app_settings WHERE id = 1"))
        row = result.fetchone()
        if not row:
            return deepcopy(DEFAULT_SETTINGS)

        data = row._mapping["data"] or {}
        merged = deepcopy(DEFAULT_SETTINGS)
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
        return merged

    async def update_settings(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = await self.get_settings()
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                current[key].update(value)
            else:
                current[key] = value

        await self.db.execute(
            text(
                """
                INSERT INTO app_settings (id, data, updated_at)
                VALUES (1, :data, NOW())
                ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                """
            ),
            {"data": current},
        )
        await self.db.commit()
        return current

    async def get_llm_settings(self) -> Dict[str, Any]:
        settings = await self.get_settings()
        return settings.get("llm", {})

    async def get_provider_priorities(self) -> list[str]:
        llm_settings = await self.get_llm_settings()
        priority = [
            llm_settings.get("primary_provider", "ollama"),
            llm_settings.get("fallback_1", "groq"),
            llm_settings.get("fallback_2", "gemini"),
        ]
        seen = set()
        result = []
        for provider in priority:
            if provider and provider not in seen:
                seen.add(provider)
                result.append(provider)
        return result
