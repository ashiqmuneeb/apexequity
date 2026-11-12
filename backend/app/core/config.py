import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Base filesystem resolution
# backend/app/core/config.py -> parents[2] is backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"

load_dotenv(ENV_PATH)


class Settings:
    PROJECT_NAME: str = "Financial Stock Analysis Engine"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Server configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))

    # Core Directories
    BACKEND_PATH: Path = BACKEND_DIR
    ARTICLES_DIR: Path = BACKEND_DIR / "articles"
    STORAGE_DIR: Path = BACKEND_DIR / "storage"
    FRONTEND_DIST_DIR: Path = BACKEND_DIR.parent / "frontend" / "dist"
    ENV_FILE_PATH: Path = ENV_PATH

    # AI Models
    DEFAULT_GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    DEFAULT_EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"
    SIMILARITY_TOP_K: int = 3

    @classmethod
    def get_groq_api_key(cls, override_key: Optional[str] = None) -> Optional[str]:
        """Resolves active Groq API Key from override, memory, or .env."""
        key = (override_key or "").strip()
        if not key:
            key = os.getenv("GROQ_API_KEY", "").strip()
        if key and key != "your_free_groq_api_key_here":
            return key
        return None

    @classmethod
    def set_groq_api_key(cls, new_key: str) -> None:
        """Sets Groq API key in process environment and persists to .env."""
        clean_key = new_key.strip()
        os.environ["GROQ_API_KEY"] = clean_key

        lines = []
        if cls.ENV_FILE_PATH.exists():
            with open(cls.ENV_FILE_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.startswith("GROQ_API_KEY="):
                new_lines.append(f"GROQ_API_KEY={clean_key}\n")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"GROQ_API_KEY={clean_key}\n")

        with open(cls.ENV_FILE_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)


settings = Settings()

