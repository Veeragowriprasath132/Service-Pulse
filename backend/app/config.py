"""
app/config.py — Centralised settings loaded from .env
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "ServiceDesk HQ"
    app_version: str = "2.0.0"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"

    # Database
    database_url: str = "sqlite:///./servicedesk.db"

    # Anthropic
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500"

    # Logging
    log_level: str = "INFO"

    # ML / RAG
    embedding_model: str = "all-MiniLM-L6-v2"
    max_context_chunks: int = 5
    chunk_size: int = 512
    routing_model_path: str = "app/ai/models/routing_model.pkl"
    sla_model_path: str = "app/ai/models/sla_model.pkl"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
