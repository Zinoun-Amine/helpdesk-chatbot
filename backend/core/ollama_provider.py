import json
import logging
import httpx
from typing import List, Dict, Any, AsyncGenerator
from core.llm_provider import LLMProvider
from config import settings

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """
    Implémentation de l'interface LLMProvider pour Ollama.
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.api_key = settings.OLLAMA_API_KEY
        self.client = httpx.AsyncClient(timeout=45.0)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": settings.OLLAMA_NUM_PREDICT,
            }
        }
        if self.model.startswith("gpt-oss"):
            # GPT-OSS réserve sinon parfois tout le budget au champ
            # `thinking`, sans produire de contenu exploitable.
            payload["think"] = "low"
        
        try:
            response = await self.client.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            if not content or not content.strip():
                raise ValueError("Ollama a retourné une réponse vide")
            return content
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Ollama chat: {e}")
            raise

    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": settings.OLLAMA_NUM_PREDICT,
            }
        }
        if self.model.startswith("gpt-oss"):
            payload["think"] = "low"
        
        try:
            async with self.client.stream("POST", url, headers=self._get_headers(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                yield chunk["message"]["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"Erreur de décodage JSON pour la ligne: {line}")
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Ollama chat_stream: {e}")
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
        
        try:
            result_str = await self.chat(messages, temperature=0.1)
            # Nettoyer la réponse pour s'assurer qu'elle est bien du JSON
            # Ollama peut parfois encadrer le JSON de backticks ```json ... ```
            result_str = result_str.strip()
            if result_str.startswith("```json"):
                result_str = result_str[7:]
            if result_str.endswith("```"):
                result_str = result_str[:-3]
            result_str = result_str.strip()
            
            result = json.loads(result_str)
            if not isinstance(result, dict):
                raise ValueError("Ollama a retourné un JSON de classification invalide")
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la classification: {e}")
            # Propager l'erreur afin que FallbackProvider puisse essayer Groq/Gemini.
            raise

    async def close(self):
        await self.client.aclose()
