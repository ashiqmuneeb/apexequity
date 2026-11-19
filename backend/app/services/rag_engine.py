import re
import time

from fastapi import HTTPException
from llama_index.core import PromptTemplate
from llama_index.llms.groq import Groq

from app.core.config import settings
from app.core.logger import logger


QA_PROMPT_TEMPLATE = PromptTemplate(
    "You are ApexEquity, an institutional financial research analyst.\n"
    "Answer the inquiry strictly and solely based on the VERIFIED FACTS and retrieved filing context provided below.\n\n"
    "Rules:\n"
    "1. Numbers and financial metrics may ONLY come from VERIFIED FACTS or from the retrieved text chunks below. Never extrapolate, speculate, or invent financial figures.\n"
    "2. Cite your sources inline using [1], [2], etc., corresponding to the numbered context passages.\n"
    "3. Include prior-year values from VERIFIED FACTS so growth rates and margin changes can be stated accurately.\n"
    "4. If the retrieved context and VERIFIED FACTS do not contain the answer, or if the question asks about a specific time period (e.g. 2012) not covered in the context, reply EXACTLY:\n"
    '   "Not disclosed in the retrieved filings."\n'
    "   Do not attempt to answer questions about uncovered years or missing metrics using other years' data.\n"
    "5. Format financial comparisons and data points clearly with proper institutional rigor.\n\n"
    "Context information is below:\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given this information, please answer the question: {query_str}\n"
    "Answer:"
)


class RAGEngineService:
    """Manages Groq LLM integration with automatic fallback, tenacity retries,

    and strict 429 rate limit error mapping with Retry-After header parsing.
    """

    def __init__(self):
        self._cached_llm: Groq | None = None
        self._cached_api_key: str | None = None
        self._active_model_name: str | None = None

    def invalidate_cache(self) -> None:
        """Clears cached query engine when index is rebuilt or key is changed."""
        logger.info("Invalidating cached RAG QueryEngine")
        self._cached_llm = None
        self._cached_api_key = None
        self._active_model_name = None

    @property
    def active_model_name(self) -> str:
        return self._active_model_name or settings.GROQ_MODEL

    @staticmethod
    def parse_retry_after(error: Exception) -> int:
        """Parses Retry-After value in seconds from Groq 429 response or error message (Condition 6)."""
        # 1. Check response headers if present on exception
        response = getattr(error, "response", None)
        if response is not None and hasattr(response, "headers"):
            headers = response.headers
            ra = headers.get("retry-after") or headers.get("Retry-After")
            if ra:
                try:
                    return int(float(ra))
                except ValueError:
                    pass

        # 2. Check string message for "try again in Xs" or "retry after X seconds"
        err_msg = str(error)
        match = re.search(r"try again in\s*([0-9.]+)\s*s", err_msg, re.IGNORECASE)
        if match:
            try:
                return max(1, int(float(match.group(1))))
            except ValueError:
                pass

        match_sec = re.search(r"retry after\s*([0-9.]+)\s*s", err_msg, re.IGNORECASE)
        if match_sec:
            try:
                return max(1, int(float(match_sec.group(1))))
            except ValueError:
                pass

        return 5  # Fallback default if unspecified

    def generate_completion(
        self,
        prompt: str,
        override_key: str | None = None,
    ) -> str:
        """Executes LLM completion across configured Groq models with fallback and retry backoff."""
        groq_key = settings.get_groq_api_key(override_key)
        if not groq_key:
            raise HTTPException(
                status_code=400,
                detail="GROQ_API_KEY is not configured. Provide it in .env or via request payload.",
            )

        candidate_models = [
            settings.GROQ_MODEL,
            settings.GROQ_FALLBACK_MODEL,
            "openai/gpt-oss-20b",
            "llama-3.1-8b-instant",
        ]
        unique_models: list[str] = []
        for m in candidate_models:
            if m and m not in unique_models:
                unique_models.append(m)

        last_error: Exception | None = None
        retry_after_sec = 5

        for model_name in unique_models:
            # Attempt up to 2 tries per model with exponential backoff on transient errors
            for attempt in range(2):
                try:
                    logger.info(
                        f"Executing Groq completion with model '{model_name}' (temp: {settings.TEMPERATURE})..."
                    )
                    llm = Groq(
                        model=model_name,
                        api_key=groq_key,
                        temperature=settings.TEMPERATURE,
                    )
                    resp = llm.complete(prompt)
                    self._active_model_name = model_name
                    self._cached_llm = llm
                    self._cached_api_key = groq_key
                    return str(resp).strip()
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    is_rate_limit = "429" in err_str or "rate limit" in err_str.lower()
                    if is_rate_limit:
                        retry_after_sec = self.parse_retry_after(e)
                        logger.warning(
                            f"Groq 429 Rate Limit on model '{model_name}' (attempt {attempt + 1}). Retry-After: {retry_after_sec}s."
                        )
                        if attempt == 0:
                            time.sleep(min(retry_after_sec, 3))
                            continue
                        # If attempt 1 also rate limits, fall back to next model
                        break
                    elif "404" in err_str or "not found" in err_str.lower() or "500" in err_str or "502" in err_str:
                        logger.warning(
                            f"Groq model '{model_name}' failed with {e}. Falling back to next candidate model..."
                        )
                        break
                    else:
                        logger.warning(f"Groq call failed on '{model_name}': {e}")
                        break

        # If all candidates failed: map upstream error cleanly
        err_msg = str(last_error) if last_error else "All Groq model candidates failed."
        if "429" in err_msg or "rate limit" in err_msg.lower():
            raise HTTPException(
                status_code=429,
                detail=f"Groq API rate limit exceeded. Retry after {retry_after_sec} seconds.",
                headers={"Retry-After": str(retry_after_sec)},
            )

        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate completion from Groq LLM: {err_msg}",
        )


rag_engine_service = RAGEngineService()
