from typing import Optional
from fastapi import HTTPException
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.config import settings
from app.core.logger import logger


class RAGEngineService:
    """Manages LlamaIndex query engine lifecycle, embeddings, and Groq LLM integration."""

    def __init__(self):
        self._cached_query_engine = None
        self._cached_api_key = None

    def invalidate_cache(self) -> None:
        """Clears cached query engine when index is rebuilt or key is changed."""
        logger.info("Invalidating cached RAG QueryEngine")
        self._cached_query_engine = None
        self._cached_api_key = None

    def get_query_engine(self, override_key: Optional[str] = None, force_reload: bool = False):
        """Retrieves or creates a query engine connected to persisted vector store."""
        groq_key = settings.get_groq_api_key(override_key)
        if not groq_key:
            raise HTTPException(
                status_code=400,
                detail="GROQ_API_KEY is not configured. Provide it in .env or via UI settings.",
            )

        storage_path = settings.STORAGE_DIR
        if not storage_path.exists() or not any(storage_path.iterdir()):
            raise HTTPException(
                status_code=400,
                detail="Vector storage index not found. Please trigger 'Rebuild Index' first.",
            )

        if self._cached_query_engine is not None and not force_reload and self._cached_api_key == groq_key:
            return self._cached_query_engine

        try:
            logger.info("Initializing LlamaIndex Settings with Groq and local BGE embeddings...")
            
            # Select Groq model (fallback support)
            groq_model = settings.DEFAULT_GROQ_MODEL
            try:
                Settings.llm = Groq(model=groq_model, api_key=groq_key)
            except Exception:
                fallback_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
                for fm in fallback_models:
                    try:
                        Settings.llm = Groq(model=fm, api_key=groq_key)
                        groq_model = fm
                        break
                    except Exception:
                        continue

            Settings.embed_model = HuggingFaceEmbedding(model_name=settings.DEFAULT_EMBED_MODEL)

            storage_context = StorageContext.from_defaults(persist_dir=str(storage_path))
            index = load_index_from_storage(storage_context)
            query_engine = index.as_query_engine(similarity_top_k=settings.SIMILARITY_TOP_K)

            self._cached_query_engine = query_engine
            self._cached_api_key = groq_key
            logger.info("RAG QueryEngine successfully initialized and cached.")
            return query_engine
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

