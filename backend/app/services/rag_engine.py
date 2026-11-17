from fastapi import HTTPException
from llama_index.core import (
    Settings,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.prompts import PromptTemplate
from llama_index.core.vector_stores.types import (
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logger import logger


QA_PROMPT_TEMPLATE = PromptTemplate(
    "You are ApexEquity, an institutional financial research analyst.\n"
    "Answer the inquiry strictly and solely based on the retrieved filing context provided below.\n"
    "Rules:\n"
    "1. Answer ONLY using the facts, figures, and statements in the context.\n"
    "2. Cite your sources inline using [1], [2], etc., corresponding to the retrieved context chunks.\n"
    "3. If the retrieved context does not contain the answer, reply exactly:\n"
    '   "Not disclosed in the retrieved filings."\n'
    "4. Never extrapolate, speculate, or invent financial figures.\n\n"
    "Context information is below:\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given this information, please answer the question: {query_str}\n"
    "Answer:"
)


class RAGEngineService:
    """Manages LlamaIndex query engine lifecycle, embeddings, model validation,

    and Groq LLM integration with automatic fallback and tenacity retries.
    """

    def __init__(self):
        self._cached_index = None
        self._cached_llm: LLM | None = None
        self._cached_embed_model: BaseEmbedding | None = None
        self._cached_api_key: str | None = None
        self._active_model_name: str | None = None

    def invalidate_cache(self) -> None:
        """Clears cached query engine when index is rebuilt or key is changed."""
        logger.info("Invalidating cached RAG QueryEngine and index")
        self._cached_index = None
        self._cached_llm = None
        self._cached_api_key = None
        self._active_model_name = None

    @property
    def active_model_name(self) -> str:
        return self._active_model_name or settings.GROQ_MODEL

    def _test_llm_call(self, llm_instance: Groq) -> None:
        """Runs a cheap test call with tenacity retry on transient errors."""

        @retry(
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            reraise=True,
        )
        def _execute():
            llm_instance.complete("ping")

        _execute()

    def _validate_and_get_llm(self, groq_key: str) -> tuple[Groq, str]:
        """Instantiates the configured Groq model, performs a cheap test call at first use,

        and falls back to safe alternates if the primary model fails.
        """
        primary_model = settings.GROQ_MODEL
        candidates = [
            primary_model,
            settings.GROQ_FALLBACK_MODEL,
            "openai/gpt-oss-20b",
            "llama-3.1-8b-instant",
        ]
        # De-duplicate while preserving order
        unique_candidates: list[str] = []
        for c in candidates:
            if c and c not in unique_candidates:
                unique_candidates.append(c)

        last_error = None
        for model_name in unique_candidates:
            try:
                logger.info(
                    f"Testing Groq model '{model_name}' with temperature {settings.TEMPERATURE}..."
                )
                llm = Groq(
                    model=model_name,
                    api_key=groq_key,
                    temperature=settings.TEMPERATURE,
                )
                self._test_llm_call(llm)
                logger.info(f"Groq model '{model_name}' successfully validated.")
                return llm, model_name
            except Exception as e:
                last_error = e
                logger.error(
                    f"Groq model '{model_name}' failed validation test call: {e}."
                )
                continue

        raise HTTPException(
            status_code=502,
            detail=(
                f"Failed to initialize any Groq LLM model. Last error: {last_error}"
            ),
        )

    def get_query_engine(
        self,
        override_key: str | None = None,
        ticker: str | None = None,
        force_reload: bool = False,
    ):
        """Retrieves or creates a query engine connected to persisted vector store,

        with optional ticker metadata filtering and strict QA citation prompt.
        """
        groq_key = settings.get_groq_api_key(override_key)
        if not groq_key:
            raise HTTPException(
                status_code=400,
                detail="GROQ_API_KEY is not configured. Provide it in .env or via request payload.",
            )

        storage_path = settings.STORAGE_DIR
        if not storage_path.exists() or not any(storage_path.iterdir()):
            raise HTTPException(
                status_code=400,
                detail="Vector storage index not found. Please trigger 'Rebuild Index' first.",
            )

        # Configure global chunking and node parsing
        Settings.node_parser = SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        try:
            # Re-initialize LLM if key changed or not cached
            if (
                self._cached_llm is None
                or self._cached_api_key != groq_key
                or force_reload
            ):
                llm, model_name = self._validate_and_get_llm(groq_key)
                self._cached_llm = llm
                self._active_model_name = model_name
                self._cached_api_key = groq_key
                Settings.llm = llm

            # Re-initialize Embeddings if not cached
            if self._cached_embed_model is None:
                embed_model = HuggingFaceEmbedding(
                    model_name=settings.DEFAULT_EMBED_MODEL
                )
                self._cached_embed_model = embed_model
                Settings.embed_model = embed_model

            # Load index if not cached
            if self._cached_index is None or force_reload:
                logger.info(f"Loading VectorStoreIndex from {storage_path}...")
                storage_context = StorageContext.from_defaults(
                    persist_dir=str(storage_path)
                )
                self._cached_index = load_index_from_storage(storage_context)

            # Build query engine with optional metadata filter by ticker
            kwargs = {
                "similarity_top_k": settings.SIMILARITY_TOP_K,
                "text_qa_template": QA_PROMPT_TEMPLATE,
            }

            if ticker and ticker.strip():
                clean_ticker = ticker.strip().upper()
                kwargs["filters"] = MetadataFilters(
                    filters=[
                        MetadataFilter(
                            key="ticker",
                            value=clean_ticker,
                            operator=FilterOperator.EQ,
                        )
                    ]
                )

            return self._cached_index.as_query_engine(**kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to initialize RAG QueryEngine: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load query engine: {str(e)}",
            )


# Singleton service instance
rag_engine_service = RAGEngineService()
