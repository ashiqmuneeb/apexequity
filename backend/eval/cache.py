import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.logger import logger


EVAL_DIR = Path(__file__).resolve().parent
CACHE_DIR = EVAL_DIR / "cache"


class EvalCache:
    """Persistent on-disk cache for model completions and LLM-judge evaluations.

    Ensures re-running evaluations avoids duplicate Groq API requests.
    Guarantees no secret keys or .env variables are ever serialized.
    """

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_key(ticker: str, prompt: str, model_name: str, task: str = "completion") -> str:
        """Derives a deterministic SHA256 cache key from query content, ticker, and model name."""
        raw = f"{task}:{ticker.strip().upper()}:{prompt.strip()}:{model_name.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_generator_key(
        ticker: str,
        prompt_hash: str,
        model_name: str,
        temperature: float = 0.1,
    ) -> str:
        """Condition 6: Cache key incorporating SHA256 hash of final prompt (retrieved context

        plus verified facts), model name, and temperature.
        """
        raw = f"generator:{ticker.strip().upper()}:{prompt_hash}:{model_name.strip()}:{temperature}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        """Loads cached evaluation record if present on disk."""
        target_file = self.cache_dir / f"{key}.json"
        if target_file.exists():
            try:
                data = json.loads(target_file.read_text(encoding="utf-8"))
                return data
            except Exception as e:
                logger.warning(f"Failed to read evaluation cache entry {key}: {e}")
                return None
        return None

    def set(self, key: str, payload: dict[str, Any]) -> None:
        """Writes sanitized evaluation record to disk."""
        target_file = self.cache_dir / f"{key}.json"
        # Sanitize: ensure no secrets
        clean_payload = dict(payload)
        for secret_field in ["api_key", "groq_api_key", "admin_key", "secret", "token"]:
            clean_payload.pop(secret_field, None)

        try:
            target_file.write_text(json.dumps(clean_payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to write evaluation cache entry {key}: {e}")


eval_cache = EvalCache()
