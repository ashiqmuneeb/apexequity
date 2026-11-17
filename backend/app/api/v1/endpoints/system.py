from fastapi import APIRouter, Depends

from app.api.deps import get_article_service, get_rag_engine_service
from app.core.config import settings
from app.schemas.system import (
    ModelMetadata,
    SystemStatusResponse,
)
from app.services.article_service import ArticleService
from app.services.rag_engine import RAGEngineService


router = APIRouter(tags=["System & Configuration"])


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    article_svc: ArticleService = Depends(get_article_service),
    rag_svc: RAGEngineService = Depends(get_rag_engine_service),
):
    """Provides system health, Groq API key presence, and vector storage readiness."""
    has_key = bool(settings.get_groq_api_key())
    index_exists = settings.STORAGE_DIR.exists() and any(
        settings.STORAGE_DIR.iterdir()
    )
    articles = [a.ticker for a in article_svc.list_articles()]

    return SystemStatusResponse(
        status="ready" if (has_key and index_exists) else "setup_required",
        has_groq_key=has_key,
        index_initialized=index_exists,
        indexed_articles_count=len(articles),
        articles=articles,
        models=ModelMetadata(
            llm=f"{rag_svc.active_model_name} (Groq)",
            embedding=f"{settings.DEFAULT_EMBED_MODEL} (Local HuggingFace)",
        ),
    )
