from typing import Dict, List
from pydantic import BaseModel, Field


class ModelMetadata(BaseModel):
    llm: str
    embedding: str


class SystemStatusResponse(BaseModel):
    status: str
    has_groq_key: bool
    index_initialized: bool
    indexed_articles_count: int
    articles: List[str]
    models: ModelMetadata


class KeyConfigPayload(BaseModel):
    groq_api_key: str = Field(..., description="Groq API Key (gsk_...)")


class KeyConfigResponse(BaseModel):
    message: str
    has_groq_key: bool


class RebuildIndexResponse(BaseModel):
    message: str
    document_chunks: int
    indexed_files: List[str]

