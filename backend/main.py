import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.chat import router as chat_router
from api.tickets import router as tickets_router
from api.knowledge_base import router as kb_router
from api.dashboard import router as dashboard_router
from api.settings import router as settings_router
from api.conversations import router as conversations_router
from api.auth import router as auth_router

# Pour le lifespan
from api.chat import vector_store, cache_service, llm_provider, glpi_client
from rag.knowledge_loader import load_knowledge_base
from db.migrations import apply_migrations
from db.database import engine

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application FastAPI.
    Exécuté au démarrage et à l'arrêt.
    """
    logger.info(f"Démarrage de {settings.APP_NAME}...")
    if settings.OLLAMA_ONLY:
        logger.info("Mode Ollama seul activé : PostgreSQL ignoré, RAG local activé.")
    else:
        await apply_migrations(engine)

    # ChromaDB est utilisé si disponible, sinon VectorStore utilise son index local.
    await load_knowledge_base(vector_store)
    
    yield
    
    # Nettoyage à l'arrêt
    logger.info("Arrêt de l'application. Fermeture des ressources...")
    await cache_service.close()
    await llm_provider.close()
    if glpi_client is not None:
        await glpi_client.close()
    # Le moteur DB asyncpg gère son propre pool, pas besoin de le fermer manuellement ici si on utilise sessionmaker,
    # mais en production on pourrait faire engine.dispose()
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API pour le Chatbot Helpdesk AUTOHALL",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # Autorise le frontend depuis localhost ou une autre machine du réseau local.
    allow_origin_regex=r"https?://[^/]+(?::\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routeurs
app.include_router(chat_router)
app.include_router(tickets_router)
app.include_router(kb_router)
app.include_router(dashboard_router)
app.include_router(settings_router)
app.include_router(conversations_router)
app.include_router(auth_router)

@app.get("/health")
async def health_check():
    """
    Endpoint de vérification de l'état de santé du backend.
    """
    return {"status": "ok", "app": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
