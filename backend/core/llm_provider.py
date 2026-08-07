from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator

class LLMProvider(ABC):
    """
    Interface abstraite pour les fournisseurs de modèles de langage (LLM).
    """

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """
        Envoie une requête de chat et retourne la réponse complète.
        """
        pass

    @abstractmethod
    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> AsyncGenerator[str, None]:
        """
        Envoie une requête de chat et retourne la réponse sous forme de flux (stream).
        """
        pass

    @abstractmethod
    async def classify(self, text: str, categories: List[str]) -> Dict[str, Any]:
        """
        Classifie le texte donné selon les catégories fournies.
        """
        pass
