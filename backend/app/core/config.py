import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Base filesystem resolution
# backend/app/core/config.py -> parents[2] is backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Financial Stock Analysis Engine"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Server configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Core Directories
    BACKEND_PATH: Path = BACKEND_DIR
    ARTICLES_DIR: Path = BACKEND_DIR / "articles"
    STORAGE_DIR: Path = BACKEND_DIR / "storage"
    FRONTEND_DIST_DIR: Path = BACKEND_DIR.parent / "frontend" / "dist"
    ENV_FILE_PATH: Path = ENV_PATH

    # AI Models & Retrieval Hyperparameters
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    DEFAULT_GROQ_MODEL: str = "openai/gpt-oss-120b"
    DEFAULT_EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"
    TEMPERATURE: float = 0.1
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    SIMILARITY_TOP_K: int = 3

    # Security & CORS
    ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )
    ADMIN_API_KEY: str | None = None

    def get_allowed_origins(self) -> list[str]:
        """Parses comma-separated allowed origins into a clean string list."""
        if not self.ALLOWED_ORIGINS:
            return ["http://localhost:5173", "http://127.0.0.1:5173"]
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    def get_groq_api_key(self, override_key: str | None = None) -> str | None:
        """Resolves active Groq API Key from per-request override or environment."""
        key = (override_key or "").strip()
        if not key:
            key = (self.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")).strip()
        if key and key != "your_free_groq_api_key_here":
            return key
        return None


settings = Settings()
# Ensure backwards compatibility for references to DEFAULT_GROQ_MODEL
settings.DEFAULT_GROQ_MODEL = settings.GROQ_MODEL
