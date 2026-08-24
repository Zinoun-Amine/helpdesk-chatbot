from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    # Paramètres de l'application
    APP_NAME: str = "AUTOHALL Helpdesk API"
    DEBUG: bool = False
    
    # Base de données PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/helpdesk"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Ollama LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gpt-oss:20b"
    OLLAMA_API_KEY: str | None = None
    OLLAMA_ONLY: bool = False
    # Larger generation windows prevent Ollama from stopping mid-answer.
    OLLAMA_NUM_PREDICT: int = 512

    # GLPI REST API v1
    GLPI_ENABLED: bool = False
    GLPI_BASE_URL: str = ""
    GLPI_APP_TOKEN: str | None = None
    GLPI_USER_TOKEN: str | None = None
    GLPI_USERNAME: str | None = None
    GLPI_PASSWORD: str | None = None
    GLPI_ENTITY_ID: int | None = None
    GLPI_REQUESTER_ID: int | None = None

    # SMTP
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = ""
    SMTP_RECIPIENT: str = ""
    SMTP_USE_TLS: bool = False
    SMTP_USE_STARTTLS: bool = True
    SMTP_AUTO_SEND: bool = False
    
    # Autres Providers (Fallback)
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Fallback configuration
    ENABLE_FALLBACK: bool = True
    PROVIDER_PRIORITY: List[str] = ["ollama", "groq", "gemini"]
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # Embedding model for the RAG knowledge base.
    # Default = French-capable multilingual MiniLM (better French synonyms than
    # Chroma's built-in English-leaning default).
    # Set KB_USE_DEFAULT_EMBEDDING=true to opt out and use Chroma's default.
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    KB_USE_DEFAULT_EMBEDDING: bool = False

    # Hybrid retrieval (chunking + BM25 + semantic merge)
    KB_CHUNK_SIZE: int = 220            # chunk size in words
    KB_CHUNK_OVERLAP: int = 40          # overlap between consecutive chunks (words)
    KB_SEMANTIC_WEIGHT: float = 0.7     # weight of semantic (Chroma) score
    KB_BM25_WEIGHT: float = 0.3         # weight of BM25 score in the hybrid merge
    KB_HYBRID_MIN_SCORE: float = 0.25   # threshold below which a hybrid result is dropped

    # Optional cross-encoder reranker (Phase 3).
    # OFF by default — small CPU/RAM cost, ~50–200ms extra latency on first call.
    # Set KB_RERANKER_ENABLED=true to activate. Pairs each candidate with the
    # query and reorders by the cross-encoder score (more accurate than cosine).
    KB_RERANKER_ENABLED: bool = False
    KB_RERANKER_MODEL: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    KB_RERANKER_TOP_N: int = 10         # max candidates to rerank (cap for latency)
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Auth / JWT
    # ⚠️ JWT_SECRET_KEY DOIT être changé en production via la variable d'env.
    JWT_SECRET_KEY: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h par défaut
    
    # Rate Limiting & Cache
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW: int = 60  # secondes
    CACHE_TTL_MINUTES: int = 60

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        """Ignore generic DEBUG=release environment values from local tooling."""
        if isinstance(value, str) and value.strip().lower() in {"release", "production", "prod", "off", "no"}:
            return False
        return value
    
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
