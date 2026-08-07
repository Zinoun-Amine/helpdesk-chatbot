import json
import logging
import httpx
from typing import List, Dict, Any, AsyncGenerator
from core.llm_provider import LLMProvider
from config import settings

logger = logging.getLogger(__name__)

class GroqProvider(LLMProvider):
    """
    Implémentation de l'interface LLMProvider pour Groq (compatible OpenAI).
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY n'est pas configurée.")
        
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = settings.GROQ_MODEL
        self.client = httpx.AsyncClient(timeout=30.0)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature
        }
        
        try:
            response = await self.client.post(self.base_url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise ValueError("Groq a retourné une réponse vide")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP Groq: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Groq chat: {e}")
            raise

    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature
        }
        
        try:
            async with self.client.stream("POST", self.base_url, headers=self._get_headers(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"Erreur de décodage JSON pour la ligne Groq: {line}")
        except httpx.HTTPStatusError as e:
            # Pour lire le body d'une erreur en streaming, il faut lire la réponse
            await response.aread()
            logger.error(f"Erreur HTTP Groq stream: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Groq chat_stream: {e}")
            raise

    async def classify(self, text: str, categories: List[str]) -> Dict[str, Any]:
        """
        Classifie le texte de l'utilisateur. Retourne un dictionnaire structuré.
        """
        prompt = (
            f"Tu es un expert du support IT (Helpdesk). Analyse ce problème utilisateur: '{text}'.\n"
            f"Choisis la meilleure catégorie parmi cette liste: {categories}.\n"
            "Détermine également le type (1 pour Incident, 2 pour Demande), la priorité (1 à 6, 1 étant le plus urgent) et la criticité (Haute, Moyenne, Basse).\n"
            "Si le problème est ambigu ou qu'il manque des informations pour classifier avec certitude, mets needs_clarification à true et confidence à un score bas.\n"
            "Réponds UNIQUEMENT avec un objet JSON valide contenant les clés: 'type' (entier), 'category' (chaîne), 'priority' (entier), 'criticality' (chaîne), 'confidence' (flottant entre 0 et 1), 'needs_clarification' (booléen). Ne mets aucun autre texte."
        )

        messages = [{"role": "user", "content": prompt}]
        
        # Pour forcer le JSON sur Groq
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            response = await self.client.post(self.base_url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            result_str = data["choices"][0]["message"]["content"]
            result = json.loads(result_str)
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la classification via Groq: {e}")
            raise

    async def close(self):
        await self.client.aclose()
