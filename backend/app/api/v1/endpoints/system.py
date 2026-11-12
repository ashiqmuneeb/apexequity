from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_article_service, get_rag_engine_service
from app.core.config import settings
from app.schemas.system import (
    KeyConfigPayload,
    KeyConfigResponse,
    ModelMetadata,
    SystemStatusResponse,
)
from app.services.article_service import ArticleService
from app.services.rag_engine import RAGEngineService

router = APIRouter(tags=["System & Configuration"])


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(service: ArticleService = Depends(get_article_service)):
    """Provides system health, Groq API key presence, and vector storage readiness."""
    has_key = bool(settings.get_groq_api_key())
    index_exists = settings.STORAGE_DIR.exists() and any(settings.STORAGE_DIR.iterdir())
    articles = [a.ticker for a in service.list_articles()]

    return SystemStatusResponse(
        status="ready" if (has_key and index_exists) else "setup_required",
        has_groq_key=has_key,
        index_initialized=index_exists,
        indexed_articles_count=len(articles),
        articles=articles,
        models=ModelMetadata(
            llm=f"{settings.DEFAULT_GROQ_MODEL} (Groq)",
            embedding=f"{settings.DEFAULT_EMBED_MODEL} (Local HuggingFace)",
        ),
    )


@router.post("/config/key", response_model=KeyConfigResponse)
def update_groq_key(
    payload: KeyConfigPayload,
    rag_engine: RAGEngineService = Depends(get_rag_engine_service),
):
    """Updates and persists the Groq API key without requiring server restart."""
    key = payload.groq_api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Groq API Key cannot be empty.")

    settings.set_groq_api_key(key)
    rag_engine.invalidate_cache()

    return KeyConfigResponse(
        message="Groq API key updated successfully.",
        has_groq_key=True,
    )

