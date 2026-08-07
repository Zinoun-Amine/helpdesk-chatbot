import json
import logging
import httpx
from typing import List, Dict, Any, AsyncGenerator
from core.llm_provider import LLMProvider
from config import settings

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    """
    Implémentation de l'interface LLMProvider pour Google Gemini via l'API REST.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY n'est pas configurée.")
        
        self.model = settings.GEMINI_MODEL
        self.client = httpx.AsyncClient(timeout=30.0)

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Convertit le format OpenAI (role/content) au format Gemini (role/parts).
        """
        gemini_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"
            elif role == "system":
                # Gemini gère les instructions système différemment, mais pour simplifier dans les messages :
                role = "user"
            
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return gemini_messages

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": self._format_messages(messages),
            "generationConfig": {
                "temperature": temperature
            }
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "candidates" in data and len(data["candidates"]) > 0:
                parts = data["candidates"][0].get("content", {}).get("parts", [])
                if parts:
                    content = parts[0].get("text", "")
                    if content and content.strip():
                        return content
            raise ValueError("Gemini a retourné une réponse vide")
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP Gemini: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Gemini chat: {e}")
            raise

    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> AsyncGenerator[str, None]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        payload = {
            "contents": self._format_messages(messages),
            "generationConfig": {
                "temperature": temperature
            }
        }
        
        try:
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            if "candidates" in chunk and len(chunk["candidates"]) > 0:
                                parts = chunk["candidates"][0].get("content", {}).get("parts", [])
                                if parts:
                                    yield parts[0].get("text", "")
                        except json.JSONDecodeError:
                            logger.warning(f"Erreur de décodage JSON pour la ligne Gemini: {line}")
        except httpx.HTTPStatusError as e:
            await response.aread()
            logger.error(f"Erreur HTTP Gemini stream: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Gemini chat_stream: {e}")
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
        
        payload = {
            "contents": self._format_messages(messages),
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "candidates" in data and len(data["candidates"]) > 0:
                parts = data["candidates"][0].get("content", {}).get("parts", [])
                if parts:
                    result_str = parts[0].get("text", "")
                    return json.loads(result_str)
            raise ValueError("Réponse invalide de Gemini")
        except Exception as e:
            logger.error(f"Erreur lors de la classification via Gemini: {e}")
            raise

    async def close(self):
        await self.client.aclose()
