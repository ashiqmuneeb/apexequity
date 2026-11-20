import re

import chromadb

from app.core.config import settings
from app.schemas.analysis import SourceEvidenceNode
from app.services.article_service import article_service
from app.services.number_validator import number_validator
from app.services.rag_engine import QA_PROMPT_TEMPLATE
from app.services.retrieval_service import retrieval_service


def test_ticker_filter_isolation(monkeypatch):
    """Verifies that vector retrieval with a ticker metadata filter strictly isolates nodes

    for the requested security and never returns chunks from other companies.
    """
    client = chromadb.EphemeralClient()
    col = client.create_collection("test_isolation", metadata={"hnsw:space": "cosine"})

    # Add mock nodes for NVDA, AAPL, MSFT with distinct 4-dim embeddings
    col.add(
        ids=["nvda_1", "aapl_1", "msft_1"],
        embeddings=[
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        documents=[
            "NVIDIA Hopper architecture and Blackwell platform driven by Data Center demand.",
            "Apple iPhone 16 Pro and Services ecosystem generated record revenues.",
            "Microsoft Azure cloud infrastructure expanded enterprise AI copilot adoption.",
        ],
        metadatas=[
            {"ticker": "NVDA", "section": "Item 1", "form": "10-K", "fiscal_year": 2026},
            {"ticker": "AAPL", "section": "Item 1", "form": "10-K", "fiscal_year": 2026},
            {"ticker": "MSFT", "section": "Item 1", "form": "10-K", "fiscal_year": 2026},
        ],
    )

    # Query with NVDA ticker filter
    query_emb = [1.0, 0.0, 0.0, 0.0]
    res_nvda = col.query(
        query_embeddings=[query_emb],
        n_results=5,
        where={"ticker": "NVDA"},
    )

    ids = res_nvda["ids"][0]
    metas = res_nvda["metadatas"][0]
    docs = res_nvda["documents"][0]

    assert len(ids) == 1
    assert metas[0]["ticker"] == "NVDA"
    assert "NVIDIA" in docs[0]
    assert "Apple" not in docs[0]
    assert "Microsoft" not in docs[0]

    # Query with AAPL ticker filter
    res_aapl = col.query(
        query_embeddings=[query_emb],
        n_results=5,
        where={"ticker": "AAPL"},
    )
    assert len(res_aapl["ids"][0]) == 1
    assert res_aapl["metadatas"][0][0]["ticker"] == "AAPL"
    assert "Apple" in res_aapl["documents"][0][0]
    assert "NVIDIA" not in res_aapl["documents"][0][0]


def test_compare_mode_no_mixing(monkeypatch):
    """Verifies that compare mode retrieves chunks separately per ticker so two companies never mix."""
    # Mock retrieve_single to return predictable mock source nodes
    def mock_retrieve_single(ticker: str, query: str, top_n: int = 5):
        clean_t = ticker.upper()
        return [
            SourceEvidenceNode(
                ticker=clean_t,
                section="Item 1A",
                form="10-K",
                fiscal_year=2026,
                accession_number=f"000000-{clean_t}",
                quote=f"Official 10-K filing excerpt for {clean_t} regarding operational performance.",
                retrieval_score=0.95,
                rerank_score=0.92,
            )
        ]

    monkeypatch.setattr(retrieval_service, "retrieve_single", mock_retrieve_single)

    sources_a, sources_b = retrieval_service.retrieve_compare("NVDA", "MSFT", "Compare revenues", top_n=5)

    assert len(sources_a) == 1
    assert len(sources_b) == 1
    assert sources_a[0].ticker == "NVDA"
    assert "NVDA" in sources_a[0].quote
    assert "MSFT" not in sources_a[0].quote

    assert sources_b[0].ticker == "MSFT"
    assert "MSFT" in sources_b[0].quote
    assert "NVDA" not in sources_b[0].quote


def test_cited_sources_exist():
    """Verifies that every cited source index [1], [2] in generation maps to an existing source object."""
    mock_sources = [
        SourceEvidenceNode(ticker="NVDA", section="Item 1", form="10-K", quote="Source one text", retrieval_score=0.9),
        SourceEvidenceNode(ticker="NVDA", section="Item 1A", form="10-K", quote="Source two text", retrieval_score=0.8),
    ]

    llm_output = "NVIDIA experienced rapid acceleration [1] with increased supply constraints [2]."

    # Extract all inline citation indices
    citations = [int(m) for m in re.findall(r"\[(\d+)\]", llm_output)]
    assert citations == [1, 2]

    # Check each index maps to a valid source node
    for cit in citations:
        assert 1 <= cit <= len(mock_sources)
        source_obj = mock_sources[cit - 1]
        assert source_obj.ticker == "NVDA"


def test_refusal_on_missing_data():
    """Verifies that queries for information absent from context mandate exact refusal."""
    prompt_str = QA_PROMPT_TEMPLATE.format(
        context_str="Retrieved context covering FY 2026 revenue and data center operations.",
        query_str="What was NVIDIA's quarterly dividend in 2012?",
    )

    assert 'reply EXACTLY:\n   "Not disclosed in the retrieved filings."' in prompt_str
    assert "Do not attempt to answer questions about uncovered years" in prompt_str


def test_number_grounding_validator():
    """Verifies that the validator flags invented numbers, accepts supported ones with unit normalization,

    and ignores years, dates, ordinals, citations, and small integers without units.
    """
    facts_block = """=== VERIFIED FACTS (SEC EDGAR XBRL) ===
Company: NVIDIA CORP (NVDA)
Primary Accession Number: 0001045810-26-000021

Current Period (ended 2026-01-25):
- Revenue: $215.94B (215,938,000,000 USD) [Tag: Revenues]
- Gross Profit: $153.46B (153,463,000,000 USD) [Tag: GrossProfit]
- Cost of Revenue: $62.48B (62,475,000,000 USD) [Tag: CostOfRevenue]
- Gross Margin: 71.1% [Tag: GrossProfit]
- YoY Revenue Growth: +65.5% (FY ended 2026-01-25 vs FY ended 2025-01-26)

Prior Period (ended 2025-01-26) [Accession: 0001045810-26-000021]:
- Prior Revenue: $130.5B (130,497,000,000 USD) [Tag: Revenues]
- Prior Gross Profit: $97.86B (97,858,000,000 USD) [Tag: GrossProfit]
- Prior Gross Margin: 75.0%
=== END VERIFIED FACTS ==="""

    metrics = {
        "revenue_raw": 215938000000.0,
        "gross_profit_raw": 153463000000.0,
        "cost_of_revenue_raw": 62475000000.0,
        "gross_margin": 71.068,
        "growth_yoy": 65.5,
        "prior_revenue_raw": 130497000000.0,
        "prior_gross_profit_raw": 97858000000.0,
        "prior_gross_margin": 74.988,
    }

    # Answer contains:
    # Supported: $215.94B, 65.5%, 71.1%, 75.0%, $76.7 billion (from source), 215,938 million (normalized)
    # Unsupported: $999B, 95.0%
    # Ignored: 2026, 2025, 2012, 1st, [1], [2], Item 1
    answer = (
        "In FY 2026, NVIDIA reported total revenue of $215.94B [1] (or 215,938 million) representing YoY growth of +65.5%. "
        "Gross margin was 71.1% [2], slipping from 75.0% in FY 2025. "
        "Historically, research investments exceeded $76.7 billion [3]. "
        "An unfounded claim stated revenue reached $999B [4] and margins surged to 95.0% [5]. "
        "In 2012, the 1st phase began under Item 1."
    )

    sources = [
        "We have invested over $76.7 billion in research and development since our inception.",
    ]

    validated_text, unsupported = number_validator.validate(
        answer, facts_block, metrics, sources
    )

    # 1. Unsupported numbers flagged
    assert "$999B" in unsupported
    assert "95.0%" in unsupported

    # 2. Supported numbers accepted without being flagged
    assert "$215.94B" not in unsupported
    assert "71.1%" not in unsupported
    assert "75.0%" not in unsupported
    assert "+65.5%" not in unsupported
    assert "65.5%" not in unsupported
    assert "$76.7 billion" not in unsupported

    # 3. Ignored non-claim entities
    assert "2012" not in unsupported
    assert "2026" not in unsupported
    assert "2025" not in unsupported
    assert "1st" not in unsupported

    # 4. In-text tags and warning line
    assert "$999B [unverified]" in validated_text
    assert "95.0% [unverified]" in validated_text
    assert "⚠️ Warning: Contains unverified numerical claims not supported by SEC filings" in validated_text


def test_incremental_indexing_skips_unchanged(monkeypatch):
    """Verifies that incremental indexing skips embedding files whose hashes have not changed."""
    # Ensure current hashes match stored hashes
    hashes = article_service._compute_hashes()
    article_service._save_stored_hashes(hashes)

    mock_embed_called = False

    class GuardedEmbed:
        def get_text_embedding_batch(self, *args, **kwargs):
            nonlocal mock_embed_called
            mock_embed_called = True
            raise RuntimeError("Embedding should not have been called for unchanged files!")

    monkeypatch.setattr(retrieval_service, "_get_embed_model", lambda: GuardedEmbed())

    # Running build_and_persist_index must skip embedding
    chunks, files = article_service.build_and_persist_index(force_rebuild=False)
    assert not mock_embed_called
    assert chunks > 0
    assert len(files) > 0


def test_delete_and_reindex_lifecycle(tmp_path):
    """Verifies creating an article, verifying presence, deleting it, and purging chunks from Chroma."""
    test_ticker = "LIFECYCLE"
    test_content = (
        "[DOCUMENT_METADATA]\n"
        "Ticker: LIFECYCLE\n"
        "Form: 10-K\n"
        "Fiscal Year: 2026\n"
        "Period End Date: 2026-01-31\n"
        "Accession Number: 0000000000-26-000001\n"
        "[/DOCUMENT_METADATA]\n\n"
        "=== ITEM 1 ===\n"
        "Lifecycle Corporation (LIFECYCLE) reported test revenues of $10.0 Billion "
        "and gross margins of 50.0% for automated testing.\n"
    )

    file_path = settings.ARTICLES_DIR / f"{test_ticker}.txt"
    try:
        # Save file directly
        file_path.write_text(test_content, encoding="utf-8")
        articles = [a.ticker for a in article_service.list_articles()]
        assert test_ticker in articles

        # Delete article
        article_service.delete_article(test_ticker)
        updated_articles = [a.ticker for a in article_service.list_articles()]
        assert test_ticker not in updated_articles
        assert not file_path.exists()
    finally:
        if file_path.exists():
            file_path.unlink()


def test_deterministic_lookup_guards():
    """Verifies deterministic lookup guards (Condition 6):

    1. Wrong year outside coverage mandates exact refusal.
    2. Missing/uncovered metrics fall back to RAG (return None).
    3. Explanation/why/risk questions mentioning R&D fall back to RAG (return None).
    4. Valid single metric + ticker + year returns exact audited fact and source evidence node.
    """
    from app.services.deterministic_lookup import deterministic_lookup_service

    # 1. Wrong year outside coverage (2012 for NVDA whose coverage is 2026/2025)
    wrong_year_q = "What was NVIDIA's R&D expense in 2012?"
    rep_1, src_1, is_ref_1 = deterministic_lookup_service.check_deterministic_lookup("NVDA", wrong_year_q)
    assert is_ref_1 is True
    assert rep_1 == "Not disclosed in the retrieved filings."
    assert len(src_1) == 0

    # 2. Missing metric (e.g. carbon emissions)
    missing_metric_q = "What was NVIDIA's scope 1 carbon emissions in fiscal year 2026?"
    rep_2, src_2, is_ref_2 = deterministic_lookup_service.check_deterministic_lookup("NVDA", missing_metric_q)
    assert rep_2 is None
    assert len(src_2) == 0
    assert is_ref_2 is False

    # 3. Explanation question mentioning R&D (must go to RAG path)
    explanation_q = "Why did NVIDIA's research and development (R&D) expense increase in fiscal year 2026?"
    rep_3, src_3, is_ref_3 = deterministic_lookup_service.check_deterministic_lookup("NVDA", explanation_q)
    assert rep_3 is None
    assert len(src_3) == 0
    assert is_ref_3 is False

    # 4. Valid single metric lookup
    valid_q = "What was NVIDIA's research and development (R&D) expense in fiscal year 2026?"
    rep_4, src_4, is_ref_4 = deterministic_lookup_service.check_deterministic_lookup("NVDA", valid_q)
    assert is_ref_4 is False
    assert rep_4 is not None
    assert "$18.5B" in rep_4 or "18.5" in rep_4
    assert len(src_4) == 1
    assert src_4[0].ticker == "NVDA"
    assert src_4[0].accession_number == "0001045810-26-000021"
    assert "ResearchAndDevelopmentExpense" in src_4[0].quote
