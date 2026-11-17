from fastapi import Header, HTTPException

from app.core.config import settings
from app.services.analysis_service import AnalysisService, analysis_service
from app.services.article_service import ArticleService, article_service
from app.services.rag_engine import RAGEngineService, rag_engine_service


def get_analysis_service() -> AnalysisService:
    return analysis_service


def get_article_service() -> ArticleService:
    return article_service


def get_rag_engine_service() -> RAGEngineService:
    return rag_engine_service


def verify_admin_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> bool:
    """Verifies administrator credentials for mutation endpoints.

    Requires X-API-Key matching settings.ADMIN_API_KEY.
    """
    expected_key = settings.ADMIN_API_KEY.strip() if settings.ADMIN_API_KEY else ""
    if not expected_key:
        return True

    if not x_api_key or x_api_key.strip() != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Admin access forbidden: invalid or missing X-API-Key header.",
        )
    return True
