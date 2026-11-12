from app.services.analysis_service import AnalysisService, analysis_service
from app.services.article_service import ArticleService, article_service
from app.services.rag_engine import RAGEngineService, rag_engine_service


def get_analysis_service() -> AnalysisService:
    return analysis_service


def get_article_service() -> ArticleService:
    return article_service


def get_rag_engine_service() -> RAGEngineService:
    return rag_engine_service

