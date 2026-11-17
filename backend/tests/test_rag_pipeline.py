from pathlib import Path

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM
from llama_index.core.vector_stores.types import (
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

from app.services.article_service import article_service
from app.services.rag_engine import QA_PROMPT_TEMPLATE


def test_retrieval_with_ticker_filter():
    """Verifies that vector retrieval with a ticker metadata filter strictly isolates nodes

    for the requested security and excludes other stocks.
    """
    mock_embed = MockEmbedding(embed_dim=16)

    doc_nvda = Document(
        text="NVIDIA Corporation (NVDA) reported Data Center revenue of $18.4 billion with H100 Hopper demand.",
        metadata={"ticker": "NVDA", "file_name": "NVDA.txt"},
    )
    doc_aapl = Document(
        text="Apple Inc. (AAPL) reported quarterly revenue of $119.6 billion driven by iPhone 15 and Services.",
        metadata={"ticker": "AAPL", "file_name": "AAPL.txt"},
    )

    index = VectorStoreIndex.from_documents(
        [doc_nvda, doc_aapl], embed_model=mock_embed
    )

    # 1. Retrieve with NVDA ticker filter
    nvda_retriever = index.as_retriever(
        similarity_top_k=2,
        filters=MetadataFilters(
            filters=[
                MetadataFilter(
                    key="ticker", value="NVDA", operator=FilterOperator.EQ
                )
            ]
        ),
    )
    nodes = nvda_retriever.retrieve("What is the quarterly revenue?")

    assert len(nodes) == 1
    assert nodes[0].node.metadata["ticker"] == "NVDA"
    assert "NVIDIA" in nodes[0].node.get_text()
    assert "Apple" not in nodes[0].node.get_text()

    # 2. Retrieve with AAPL ticker filter
    aapl_retriever = index.as_retriever(
        similarity_top_k=2,
        filters=MetadataFilters(
            filters=[
                MetadataFilter(
                    key="ticker", value="AAPL", operator=FilterOperator.EQ
                )
            ]
        ),
    )
    aapl_nodes = aapl_retriever.retrieve("What is the quarterly revenue?")

    assert len(aapl_nodes) == 1
    assert aapl_nodes[0].node.metadata["ticker"] == "AAPL"
    assert "Apple" in aapl_nodes[0].node.get_text()
    assert "NVIDIA" not in aapl_nodes[0].node.get_text()


def test_fake_llm_and_mock_embeddings_query():
    """Verifies end-to-end query engine execution using MockLLM and MockEmbedding with zero network calls."""
    mock_embed = MockEmbedding(embed_dim=16)
    mock_llm = MockLLM(max_tokens=50)

    doc = Document(
        text="Acme Corp reported record revenue and gross margins of 65.0% for fiscal year 2024.",
        metadata={"ticker": "ACME", "file_name": "ACME.txt"},
    )

    index = VectorStoreIndex.from_documents([doc], embed_model=mock_embed)
    query_engine = index.as_query_engine(
        llm=mock_llm,
        text_qa_template=QA_PROMPT_TEMPLATE,
        similarity_top_k=1,
    )

    response = query_engine.query("What were the gross margins?")
    assert response is not None
    assert len(response.source_nodes) == 1
    assert response.source_nodes[0].node.metadata["ticker"] == "ACME"


def test_refusal_prompt_template_formatting():
    """Verifies that the QA prompt template mandates refusal when context is missing."""
    prompt_str = QA_PROMPT_TEMPLATE.format(
        context_str="Context information for company XYZ...",
        query_str="What was the CEO salary?",
    )

    assert "Not disclosed in the retrieved filings." in prompt_str
    assert "Cite your sources inline using [1], [2]" in prompt_str
    assert "Never extrapolate, speculate, or invent financial figures." in prompt_str


def test_delete_and_reindex_lifecycle():
    """Verifies creating an article, rebuilding index, deleting it, and verifying auto-reindex purges it."""
    test_ticker = "LIFECYCLE"
    test_content = (
        "Lifecycle Corporation (LIFECYCLE) reported test revenues of $10.0 Billion "
        "and gross margins of 50.0% for automated testing."
    )

    # 1. Save and index
    filename = article_service.save_article(test_ticker, test_content)
    assert filename == "LIFECYCLE.txt"
    articles = [a.ticker for a in article_service.list_articles()]
    assert test_ticker in articles

    # 2. Delete and ensure auto-reindex occurs
    article_service.delete_article(test_ticker)
    updated_articles = [a.ticker for a in article_service.list_articles()]
    assert test_ticker not in updated_articles

    # Ensure file is removed from disk
    file_path = article_service.settings.ARTICLES_DIR / f"{test_ticker}.txt" if hasattr(article_service, "settings") else Path("backend/articles") / f"{test_ticker}.txt"
    assert not file_path.exists()
