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
    CHROMA_DIR: Path = BACKEND_DIR / "storage" / "chroma"
    SEC_CACHE_DIR: Path = BACKEND_DIR / "storage" / "sec_cache"
    SEC_METRICS_FILE: Path = BACKEND_DIR / "storage" / "sec_metrics.json"
    FRONTEND_DIST_DIR: Path = BACKEND_DIR.parent / "frontend" / "dist"
    ENV_FILE_PATH: Path = ENV_PATH

    # SEC EDGAR Integration
    SEC_EDGAR_USER_AGENT: str | None = None

    # AI Models & Retrieval Hyperparameters
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-20b"
    DEFAULT_GROQ_MODEL: str = "openai/gpt-oss-120b"
    DEFAULT_EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"
    TEMPERATURE: float = 0.1
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    SIMILARITY_TOP_K: int = 5
    DENSE_TOP_K: int = 10
    BM25_TOP_K: int = 10
    TOP_N_RERANK: int = 5
    RRF_K: int = 60
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Section-aware priority boosting
    # Phase 4c Pre-registered Retention Rule: Disabled by default (0.0% delta on v1 and v2)
    SECTION_BOOST_VALUE: float = 0.004
    SECTION_BOOST_ENABLED: bool = False
    QUERY_EXPANSION_ENABLED: bool = False
    DETERMINISTIC_LOOKUP_ENABLED: bool = True
    # Phase 4d: Defaulted to True because table conversion is enabled and financial tables exist in the corpus
    TABLE_EXEMPTION_ENABLED: bool = True

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
