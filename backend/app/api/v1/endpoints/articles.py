from fastapi import APIRouter, Depends

from app.api.deps import get_article_service, verify_admin_key
from app.schemas.article import (
    ArticleActionResponse,
    ArticleListResponse,
    ArticlePayload,
    FetchLiveStockRequest,
    FetchLiveStockResponse,
)
from app.schemas.system import RebuildIndexResponse
from app.services.article_service import ArticleService


router = APIRouter(tags=["Articles & Filings"])


@router.post(
    "/articles/fetch-live",
    response_model=FetchLiveStockResponse,
    dependencies=[Depends(verify_admin_key)],
)
def fetch_live_stock_data(
    payload: FetchLiveStockRequest,
    service: ArticleService = Depends(get_article_service),
):
    """Fetches real-time financial statements and overview via Yahoo Finance,

    saves the document into ./articles, and embeds it into the vector database.
    Requires X-API-Key admin authorization.
    """
    result = service.fetch_live_stock_data(ticker=payload.ticker)
    return FetchLiveStockResponse(
        message=(
            f"Successfully fetched live financials for {result['company_name']} "
            f"(${result['ticker']}) and indexed into vector storage."
        ),
        ticker=result["ticker"],
        filename=result["filename"],
        company_name=result["company_name"],
        market_cap=result.get("market_cap"),
        revenue=result.get("revenue"),
        indexed_chunks=result.get("indexed_chunks", 0),
    )


@router.get("/articles", response_model=ArticleListResponse)
def list_articles(service: ArticleService = Depends(get_article_service)):
    """Retrieves all corporate reports and filings present in the corpus."""
    articles = service.list_articles()
    return ArticleListResponse(articles=articles)


@router.post(
    "/articles",
    response_model=ArticleActionResponse,
    dependencies=[Depends(verify_admin_key)],
)
def save_article(
    payload: ArticlePayload,
    service: ArticleService = Depends(get_article_service),
):
    """Saves or updates a stock document in the corpus and synchronizes index.

    Requires X-API-Key admin authorization.
    """
    filename = service.save_article(
        ticker=payload.ticker, content=payload.content
    )
    return ArticleActionResponse(
        message=f"Document for {payload.ticker.upper()} saved successfully.",
        filename=filename,
    )


@router.delete(
    "/articles/{ticker}",
    response_model=ArticleActionResponse,
    dependencies=[Depends(verify_admin_key)],
)
def delete_article(
    ticker: str,
    service: ArticleService = Depends(get_article_service),
):
    """Deletes an article file for the specified ticker and purges from vector storage.

    Requires X-API-Key admin authorization.
    """
    service.delete_article(ticker=ticker)
    return ArticleActionResponse(
        message=f"Document for {ticker.upper()} deleted successfully.",
        filename=f"{ticker.upper()}.txt",
    )


@router.post(
    "/index/rebuild",
    response_model=RebuildIndexResponse,
    dependencies=[Depends(verify_admin_key)],
)
def rebuild_index(service: ArticleService = Depends(get_article_service)):
    """Rebuilds local vector store index from the articles directory.

    Requires X-API-Key admin authorization.
    """
    doc_count, files = service.build_and_persist_index(force_rebuild=True)
    return RebuildIndexResponse(
        message="Vector index rebuilt and persisted to ./storage successfully.",
        document_chunks=doc_count,
        indexed_files=files,
    )
