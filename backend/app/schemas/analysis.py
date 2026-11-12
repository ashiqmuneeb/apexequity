from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SingleStockRequest(BaseModel):
    ticker: str = Field(..., description="Stock symbol (e.g. NVDA, GOOGL)")
    custom_prompt: Optional[str] = Field(None, description="Optional custom prompt override")
    groq_api_key: Optional[str] = Field(None, description="Optional per-request API key")


class CompareStockRequest(BaseModel):
    stock_a: str = Field(..., description="Primary stock ticker")
    stock_b: str = Field(..., description="Benchmark/comparison stock ticker")
    custom_prompt: Optional[str] = Field(None, description="Optional custom prompt override")
    groq_api_key: Optional[str] = Field(None, description="Optional per-request API key")


class CustomQueryRequest(BaseModel):
    prompt: str = Field(..., description="Natural language question across the document corpus")
    groq_api_key: Optional[str] = Field(None, description="Optional per-request API key")


class SourceEvidenceNode(BaseModel):
    score: Optional[float] = None
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    ticker: str
    prompt: str
    report: str
    sentiment: Optional[str] = Field("Bullish", description="Overall sentiment classification")
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured financial metrics")
    sources: List[SourceEvidenceNode] = Field(default_factory=list)


class ComparisonResponse(BaseModel):
    stock_a: str
    stock_b: str
    prompt: str
    report: str
    comparison_metrics: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Side-by-side KPI comparison data for charts"
    )
    sources: List[SourceEvidenceNode] = Field(default_factory=list)


class CustomQueryResponse(BaseModel):
    prompt: str
    report: str
    sources: List[SourceEvidenceNode] = Field(default_factory=list)

