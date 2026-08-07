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
    # Number of tokens / prediction budget Ollama should use. Lower values are faster.
    OLLAMA_NUM_PREDICT: int = 64

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
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
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
