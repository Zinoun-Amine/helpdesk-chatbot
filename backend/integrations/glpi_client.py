"""Client minimal et asynchrone pour l'API REST GLPI v1.

Référence : https://help.glpi-project.org/documentation/modules/configuration/general/api/api
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class GLPIConfigurationError(RuntimeError):
    """GLPI est demandé mais ses paramètres sont incomplets."""


class GLPIClient:
    def __init__(self) -> None:
        self.base_url = self._build_api_url(settings.GLPI_BASE_URL)
        self.app_token = settings.GLPI_APP_TOKEN
        self.user_token = settings.GLPI_USER_TOKEN
        self.username = settings.GLPI_USERNAME
        self.password = settings.GLPI_PASSWORD
        self.entity_id = settings.GLPI_ENTITY_ID
        self.requester_id = settings.GLPI_REQUESTER_ID
        self.client = httpx.AsyncClient(timeout=30.0)
        self._session_token: Optional[str] = None

    @staticmethod
    def _build_api_url(value: str) -> str:
        base = (value or "").rstrip("/")
        if not base:
            return ""
        return base if base.endswith("/apirest.php") else f"{base}/apirest.php"

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.app_token and (self.user_token or (self.username and self.password)))

    def _auth_headers(self) -> Dict[str, str]:
        if not self.configured:
            raise GLPIConfigurationError(
                "GLPI est activé mais GLPI_BASE_URL, GLPI_APP_TOKEN et un accès utilisateur sont requis."
            )
        headers = {"Content-Type": "application/json", "App-Token": self.app_token or ""}
        if self._session_token:
            headers["Session-Token"] = self._session_token
        return headers

    def _init_auth(self) -> Dict[str, str]:
        if self.user_token:
            return {"Authorization": f"user_token {self.user_token}"}
        encoded = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    async def _ensure_session(self) -> None:
        if self._session_token:
            return
        headers = {"Content-Type": "application/json", "App-Token": self.app_token or ""}
        headers.update(self._init_auth())
        response = await self.client.get(f"{self.base_url}/initSession/", headers=headers)
        response.raise_for_status()
        data = response.json()
        self._session_token = data.get("session_token")
        if not self._session_token:
            raise RuntimeError("GLPI n'a pas retourné de session_token")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        await self._ensure_session()
        response = await self.client.request(method, f"{self.base_url}/{path.lstrip('/')}", headers=self._auth_headers(), **kwargs)
        if response.status_code == 401:
            self._session_token = None
            await self._ensure_session()
            response = await self.client.request(method, f"{self.base_url}/{path.lstrip('/')}", headers=self._auth_headers(), **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    @staticmethod
    def _priority_to_urgency(priority: str) -> int:
        return {"Urgent": 5, "High": 4, "Medium": 3, "Low": 2}.get(priority, 3)

    async def create_ticket(self, data: Dict[str, Any]) -> Dict[str, Any]:
        input_data: Dict[str, Any] = {
            "name": data["title"],
            "content": data["description"],
            "type": int(data.get("ticket_type", 1)),
            "urgency": self._priority_to_urgency(data.get("priority", "Medium")),
            "impact": self._priority_to_urgency(data.get("priority", "Medium")),
        }
        if self.entity_id is not None:
            input_data["entities_id"] = self.entity_id
        if self.requester_id is not None:
            input_data["_users_id_requester"] = self.requester_id
        if data.get("category_id") is not None:
            input_data["itilcategories_id"] = data["category_id"]

        result = await self._request("POST", "Ticket/", json={"input": input_data})
        if isinstance(result, dict) and result.get("id"):
            return {"id": int(result["id"]), **input_data}
        raise RuntimeError(f"Réponse GLPI inattendue lors de la création : {result}")

    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"Ticket/{ticket_id}")

    async def list_tickets(self, limit: int = 100) -> list[Dict[str, Any]]:
        result = await self._request("GET", "Ticket/", params={"range": f"0-{max(limit - 1, 0)}"})
        return result if isinstance(result, list) else []

    async def update_ticket(self, ticket_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        status = data.get("status")
        glpi_status = {"Open": 1, "In Progress": 2, "Waiting for User": 3, "Resolved": 5, "Closed": 6}.get(status, status)
        allowed = {"name": data.get("title"), "content": data.get("description"), "status": glpi_status}
        input_data = {key: value for key, value in allowed.items() if value is not None}
        result = await self._request("PUT", f"Ticket/{ticket_id}", json={"input": {"id": ticket_id, **input_data}})
        if isinstance(result, dict) and result.get("status") is False:
            raise RuntimeError(f"GLPI a refusé la mise à jour du ticket {ticket_id}: {result}")
        return await self.get_ticket(ticket_id)

    async def close(self) -> None:
        await self.client.aclose()
