from pydantic import BaseModel


class ModelMetadata(BaseModel):
    llm: str
    embedding: str


class SystemStatusResponse(BaseModel):
    status: str
    has_groq_key: bool
    index_initialized: bool
    indexed_articles_count: int
    articles: list[str]
    models: ModelMetadata


class RebuildIndexResponse(BaseModel):
    message: str
    document_chunks: int
    indexed_files: list[str]
