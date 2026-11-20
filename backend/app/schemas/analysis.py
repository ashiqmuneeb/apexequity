from typing import Any

from pydantic import BaseModel, Field


class SingleStockRequest(BaseModel):
    ticker: str = Field(..., description="Stock symbol (e.g. NVDA, GOOGL)")
    custom_prompt: str | None = Field(
        None, description="Optional custom prompt override"
    )
    groq_api_key: str | None = Field(None, description="Optional per-request API key")


class CompareStockRequest(BaseModel):
    stock_a: str = Field(..., description="Primary stock ticker")
    stock_b: str = Field(..., description="Benchmark/comparison stock ticker")
    custom_prompt: str | None = Field(
        None, description="Optional custom prompt override"
    )
    groq_api_key: str | None = Field(None, description="Optional per-request API key")


class CustomQueryRequest(BaseModel):
    prompt: str = Field(
        ..., description="Natural language question across the document corpus"
    )
    groq_api_key: str | None = Field(None, description="Optional per-request API key")


class SourceEvidenceNode(BaseModel):
    ticker: str | None = None
    form: str | None = "10-K"
    fiscal_year: int | str | None = None
    period_end: str | None = None
    section: str | None = None
    accession_number: str | None = None
    quote: str = ""
    rank: int | None = Field(None, description="Retrieval rank (#1, #2, ...)")
    retrieval_score: float | None = Field(
        None, description="Dense/BM25 Reciprocal Rank Fusion retrieval score"
    )
    rerank_score: float | None = Field(
        None, description="CrossEncoder reranking score"
    )
    score: float | None = None
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    ticker: str
    prompt: str
    report: str
    sentiment: str | None = Field(
        None,
        description="Sentiment classification derived from real data, otherwise null",
    )
    metrics: dict[str, Any] | None = Field(
        None, description="Structured financial metrics or null"
    )
    sources: list[SourceEvidenceNode] = Field(default_factory=list)
    unsupported_numbers: list[str] = Field(
        default_factory=list,
        description="Numerical claims in the answer not supported by source filings",
    )
    is_sample: bool = Field(False, description="Whether this response uses sample data")
    path: str = Field("rag", description="Execution path: 'deterministic' or 'rag'")


class ComparisonResponse(BaseModel):
    stock_a: str
    stock_b: str
    prompt: str
    report: str
    comparison_metrics: list[dict[str, Any]] = Field(
        default_factory=list, description="Side-by-side KPI comparison data for charts"
    )
    sources: list[SourceEvidenceNode] = Field(default_factory=list)
    unsupported_numbers: list[str] = Field(
        default_factory=list,
        description="Numerical claims in the answer not supported by source filings",
    )
    is_sample: bool = Field(False, description="Whether this response uses sample data")
    path: str = Field("rag", description="Execution path: 'deterministic' or 'rag'")


class CustomQueryResponse(BaseModel):
    prompt: str
    report: str
    sources: list[SourceEvidenceNode] = Field(default_factory=list)
    unsupported_numbers: list[str] = Field(
        default_factory=list,
        description="Numerical claims in the answer not supported by source filings",
    )
    path: str = Field("rag", description="Execution path: 'deterministic' or 'rag'")
