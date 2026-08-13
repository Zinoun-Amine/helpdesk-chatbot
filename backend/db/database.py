import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config import settings

logger = logging.getLogger(__name__)

# Création du moteur asynchrone SQLAlchemy
# On utilise asyncpg comme driver
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=3600,  # Recycler les connexions chaque heure
)

# Fabrique de sessions asynchrones
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession | None, None]:
    """
    Fournisseur de dépendance pour obtenir une session de base de données asynchrone.
    Retourne None si OLLAMA_ONLY=True (mode sans PostgreSQL).
    """
    if settings.OLLAMA_ONLY:
        yield None
        return

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Erreur de base de données : {e}")
            raise
        finally:
            await session.close()
