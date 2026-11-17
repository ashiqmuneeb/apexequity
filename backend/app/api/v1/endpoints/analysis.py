from fastapi import APIRouter, Depends

from app.api.deps import get_analysis_service
from app.schemas.analysis import (
    AnalysisResponse,
    CompareStockRequest,
    ComparisonResponse,
    CustomQueryRequest,
    CustomQueryResponse,
    SingleStockRequest,
)
from app.services.analysis_service import AnalysisService


router = APIRouter(prefix="/analyze", tags=["Financial Analysis"])


@router.post("/single", response_model=AnalysisResponse)
def analyze_single_stock(
    payload: SingleStockRequest,
    service: AnalysisService = Depends(get_analysis_service),
):
    """Generates an automated deep-dive financial research report for a single stock."""
    return service.analyze_single_stock(
        ticker=payload.ticker,
        custom_prompt=payload.custom_prompt,
        groq_api_key=payload.groq_api_key,
    )


@router.post("/compare", response_model=ComparisonResponse)
def compare_stocks(
    payload: CompareStockRequest,
    service: AnalysisService = Depends(get_analysis_service),
):
    """Conducts a side-by-side comparative analysis between two stocks."""
    return service.compare_stocks(
        stock_a=payload.stock_a,
        stock_b=payload.stock_b,
        custom_prompt=payload.custom_prompt,
        groq_api_key=payload.groq_api_key,
    )


@router.post("/custom", response_model=CustomQueryResponse)
def custom_query(
    payload: CustomQueryRequest,
    service: AnalysisService = Depends(get_analysis_service),
):
    """Executes a natural language query across all ingested financial documents."""
    return service.custom_query(
        prompt=payload.prompt,
        groq_api_key=payload.groq_api_key,
    )

