import logging
import json
import redis.asyncio as redis
from typing import Optional, Any
from config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """
    Service pour la mise en cache (Redis) et le rate limiting.
    """

    def __init__(self):
        try:
            # Redis est optionnel en local : ses appels ne doivent jamais
            # bloquer la réponse du chatbot lorsqu'il n'est pas démarré.
            self.redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.1,
                socket_timeout=0.2,
            )
            logger.info("Connexion Redis initialisée.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Redis: {e}")
            self.redis = None

    async def get_cached_response(self, key: str) -> Optional[str]:
        """
        Récupère une réponse en cache.
        """
        if not self.redis:
            return None
        
        try:
            return await self.redis.get(f"cache:{key}")
        except Exception as e:
            logger.error(f"Erreur Redis get: {e}")
            return None

    async def set_cached_response(self, key: str, value: str, ttl: int = None):
        """
        Stocke une réponse en cache avec un TTL optionnel (en secondes).
        """
        if not self.redis:
            return
            
        if ttl is None:
            ttl = settings.CACHE_TTL_MINUTES * 60
            
        try:
            await self.redis.set(f"cache:{key}", value, ex=ttl)
        except Exception as e:
            logger.error(f"Erreur Redis set: {e}")

    async def check_rate_limit(self, client_ip: str) -> bool:
        """
        Vérifie si l'IP a dépassé la limite de requêtes (Sliding window simplifiée).
        Retourne True si c'est bon, False si bloqué.
        """
        if not self.redis:
            return True # Autoriser par défaut si Redis est down
            
        key = f"rate_limit:{client_ip}"
        limit = settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW
        
        try:
            current_count = await self.redis.get(key)
            if current_count and int(current_count) >= limit:
                return False
            return True
        except Exception as e:
            logger.error(f"Erreur Redis rate limit check: {e}")
            return True

    async def increment_rate_limit(self, client_ip: str):
        """
        Incrémente le compteur de requêtes pour une IP.
        """
        if not self.redis:
            return
            
        key = f"rate_limit:{client_ip}"
        window = settings.RATE_LIMIT_WINDOW
        
        try:
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window, nx=True) # Set expire seulement si n'a pas de TTL
            await pipe.execute()
        except Exception as e:
            logger.error(f"Erreur Redis rate limit incr: {e}")

    async def close(self):
        """
        Ferme la connexion Redis.
        """
        if self.redis:
            await self.redis.close()
