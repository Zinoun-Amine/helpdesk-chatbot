import logging
import time
import httpx
from typing import List, Dict, Any, AsyncGenerator
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class FallbackProvider(LLMProvider):
    """
    Orchestrateur de fallback pour les fournisseurs LLM.
    Essaie les fournisseurs dans l'ordre fourni.
    """

    def __init__(self, providers: Dict[str, LLMProvider], priority: List[str]):
        """
        :param providers: Dictionnaire associant un nom (ex: 'groq') à une instance de LLMProvider.
        :param priority: Liste des noms dans l'ordre de priorité (ex: ['groq', 'gemini', 'ollama']).
        """
        self.providers = providers
        self.priority = priority
        
        # Statistiques
        self.stats = {
            name: {"label": name.title(), "requests": 0, "success": 0, "fallback_triggered": 0, "errors": 0, "latency_total_ms": 0.0}
            for name in priority
        }

    def _get_recoverable_errors(self) -> tuple:
        """
        Retourne les exceptions considérées comme récupérables (qui déclenchent un fallback).
        """
        return (httpx.TimeoutException, httpx.ConnectError)

    def _is_recoverable_http_status(self, status_code: int) -> bool:
        """
        Vérifie si le code HTTP est récupérable.
        429: Too Many Requests
        500+: Erreurs serveur
        """
        return status_code == 429 or status_code >= 500

    async def _execute_with_fallback(self, method_name: str, *args, **kwargs) -> Any:
        """
        Exécute une méthode (chat ou classify) avec le mécanisme de fallback.
        """
        last_exception = None

        for provider_name in self.priority:
            if provider_name not in self.providers:
                logger.warning(f"Provider {provider_name} non configuré, ignoré.")
                continue

            provider = self.providers[provider_name]
            logger.info(f"Tentative d'exécution avec {provider_name}...")

            try:
                method = getattr(provider, method_name)
                started_at = time.perf_counter()
                result = await method(*args, **kwargs)
                if isinstance(result, str) and not result.strip():
                    raise ValueError(f"{provider_name} a retourné une réponse vide")
                elapsed_ms = (time.perf_counter() - started_at) * 1000.0
                
                self.stats[provider_name]["requests"] += 1
                self.stats[provider_name]["success"] += 1
                self.stats[provider_name]["latency_total_ms"] += elapsed_ms
                logger.info(f"Succès avec {provider_name}.")
                return result
                
            except self._get_recoverable_errors() as e:
                logger.warning(f"{provider_name} indisponible (réseau/timeout): {e}. Basculement au suivant.")
                self.stats[provider_name]["requests"] += 1
                self.stats[provider_name]["errors"] += 1
                self.stats[provider_name]["fallback_triggered"] += 1
                last_exception = e
                continue
                
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if self._is_recoverable_http_status(status):
                    logger.warning(f"{provider_name} a renvoyé une erreur {status}. Basculement au suivant.")
                    self.stats[provider_name]["requests"] += 1
                    self.stats[provider_name]["errors"] += 1
                    self.stats[provider_name]["fallback_triggered"] += 1
                    last_exception = e
                    continue
                else:
                    logger.error(f"{provider_name} a renvoyé une erreur non récupérable {status}: {e}")
                    raise e
                    
            except Exception as e:
                logger.error(f"Erreur inattendue avec {provider_name}: {e}. Basculement au suivant.")
                self.stats[provider_name]["requests"] += 1
                self.stats[provider_name]["errors"] += 1
                self.stats[provider_name]["fallback_triggered"] += 1
                last_exception = e
                continue

        logger.error("Tous les fournisseurs ont échoué.")
        if last_exception:
            raise last_exception
        raise Exception("Aucun fournisseur n'a pu répondre à la requête.")

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        return await self._execute_with_fallback("chat", messages, temperature=temperature)

    async def classify(self, text: str, categories: List[str]) -> Dict[str, Any]:
        return await self._execute_with_fallback("classify", text, categories)

    async def chat_stream(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> AsyncGenerator[str, None]:
        """
        Gère le stream avec fallback. Si le stream plante après avoir commencé à envoyer des données, 
        le fallback est complexe, donc le fallback est garanti au moment de la connexion initiale.
        """
        last_exception = None

        for provider_name in self.priority:
            if provider_name not in self.providers:
                continue

            provider = self.providers[provider_name]
            logger.info(f"Tentative de stream avec {provider_name}...")

            try:
                # Nous itérons sur le générateur. S'il y a une erreur de connexion,
                # elle devrait se déclencher lors du premier 'async for'.
                stream_gen = provider.chat_stream(messages, temperature=temperature)
                
                started = False
                try:
                    started_at = time.perf_counter()
                    async for chunk in stream_gen:
                        if not chunk:
                            continue
                        if not started:
                            logger.info(f"Connexion stream établie avec {provider_name}.")
                            started = True
                            self.stats[provider_name]["success"] += 1
                            self.stats[provider_name]["requests"] += 1
                        yield chunk
                    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
                    self.stats[provider_name]["latency_total_ms"] += elapsed_ms
                    if not started:
                        raise ValueError(f"{provider_name} a fermé le flux sans retourner de contenu")
                    return  # Terminé avec succès
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    if started:
                        logger.error(f"Le stream {provider_name} s'est interrompu en cours de route: {e}")
                        raise e # Si on a déjà commencé à envoyer, on ne peut pas relancer le fallback proprement
                    else:
                        self.stats[provider_name]["requests"] += 1
                        self.stats[provider_name]["errors"] += 1
                        self.stats[provider_name]["fallback_triggered"] += 1
                        raise e # Sera catché par le bloc parent
                except httpx.HTTPStatusError as e:
                    if started:
                        logger.error(f"Erreur HTTP pendant le stream {provider_name}: {e}")
                        raise e
                    else:
                        self.stats[provider_name]["requests"] += 1
                        self.stats[provider_name]["errors"] += 1
                        self.stats[provider_name]["fallback_triggered"] += 1
                        raise e

            except self._get_recoverable_errors() as e:
                logger.warning(f"{provider_name} indisponible pour le stream: {e}. Basculement.")
                self.stats[provider_name]["fallback_triggered"] += 1
                last_exception = e
                continue
                
            except httpx.HTTPStatusError as e:
                if self._is_recoverable_http_status(e.response.status_code):
                    logger.warning(f"{provider_name} erreur {e.response.status_code} au lancement du stream. Basculement.")
                    self.stats[provider_name]["fallback_triggered"] += 1
                    last_exception = e
                    continue
                else:
                    raise e
                    
            except Exception as e:
                logger.warning(f"Erreur avec {provider_name} pour le stream: {e}. Basculement.")
                self.stats[provider_name]["fallback_triggered"] += 1
                last_exception = e
                continue

        logger.error("Tous les fournisseurs ont échoué pour le stream.")
        if last_exception:
            raise last_exception
        raise Exception("Aucun fournisseur n'a pu ouvrir le flux.")

    async def close(self):
        for provider in self.providers.values():
            await provider.close()

    def get_stats_snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {name: stats.copy() for name, stats in self.stats.items()}
