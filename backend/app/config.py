"""Application configuration – free-tier friendly, secrets from env only."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    environment: str = "development"
    log_level: str = "INFO"
    demo_mode: bool = True
    api_secret_key: str = "dev-only-change-me"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    next_public_supabase_url: str = ""
    next_public_supabase_anon_key: str = ""

    # OpenRouter
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "busmate"

    # RAG
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_top_k: int = 4

    # Simulation flags
    payment_simulation: bool = True
    otp_simulation: bool = True

    @property
    def ai_available(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
