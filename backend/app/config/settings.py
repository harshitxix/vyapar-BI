from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/vyapar_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/vyapar_db"

    SCHEDULER_ENABLED: bool = True
    DEFAULT_POLL_INTERVAL: int = 900

    # AI Enrichment Configuration (Phase 2)
    AI_ENRICHMENT_ENABLED: bool = True
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_BATCH_SIZE: int = 5
    AI_MAX_RETRIES: int = 3
    AI_PROMPT_VERSION: str = "v1.0"


settings = Settings()
