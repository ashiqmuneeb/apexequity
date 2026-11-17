from pydantic import BaseModel, Field


class ArticlePayload(BaseModel):
    ticker: str = Field(..., description="Stock symbol associated with document")
    content: str = Field(
        ..., description="Financial statement, filing, or earnings notes"
    )


class ArticleItem(BaseModel):
    filename: str
    ticker: str
    length: int
    preview: str
    content: str


class ArticleListResponse(BaseModel):
    articles: list[ArticleItem]


class ArticleActionResponse(BaseModel):
    message: str
    filename: str


class FetchLiveStockRequest(BaseModel):
    ticker: str = Field(
        ..., description="Stock ticker symbol to pull live financials for"
    )


class FetchLiveStockResponse(BaseModel):
    message: str
    ticker: str
    filename: str
    company_name: str
    market_cap: str | None = None
    revenue: str | None = None
    indexed_chunks: int
