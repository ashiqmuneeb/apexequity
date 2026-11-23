from app.services.deterministic_lookup import (
    AggregateType,
    deterministic_lookup_service,
)


def test_intent_parsing_compound_growth_beats_revenue():
    """Compound phrase 'year-over-year net sales growth' must resolve to growth_yoy, not revenue."""
    q = "What was Apple's year-over-year net sales growth in fiscal year 2026?"
    intent = deterministic_lookup_service.parse_intent(q)
    assert intent is not None
    assert intent.metric_key == "growth_yoy"
    assert intent.aggregate_type == AggregateType.GROWTH_PERCENT


def test_deterministic_lookup_aapl_growth_value():
    """Deterministic lookup for Apple's net sales growth must return 15.1% growth, NOT total revenue."""
    q = "What was Apple's year-over-year net sales growth in fiscal year 2026?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("AAPL", q)
    assert report is not None
    assert not is_refusal
    assert "+15.1%" in report or "15.1%" in report
    assert "478.83" not in report  # Must not return total revenue
    assert len(sources) == 1
    # Check period end date, XBRL tag and accession number are present
    assert "Period ended" in report or "period ended" in report
    assert "Tag:" in report
    assert "Accession Number:" in report


def test_deterministic_lookup_gross_margin_percentage():
    """Query for gross margin percentage must return margin percent with metadata."""
    q = "What was Apple's gross margin percentage in fiscal year 2026?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("AAPL", q)
    assert report is not None
    assert not is_refusal
    assert "48.8%" in report
    assert len(sources) == 1
    assert sources[0].metadata["tag"] == "GrossProfit / Revenues" or "tag" in sources[0].metadata


def test_deterministic_lookup_operating_income():
    """Query for operating income must return dollar amount with accession."""
    q = "What was Microsoft's operating income in fiscal year 2026?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("MSFT", q)
    assert report is not None
    assert not is_refusal
    assert "$155.24B" in report
    assert len(sources) == 1
    assert sources[0].accession_number == "0001193125-26-323660"


def test_deterministic_lookup_ratio_falls_back_to_rag():
    """Queries for derived ratios (e.g. R&D as a percent of revenue) must fall back to RAG."""
    q = "What was NVIDIA's R&D expense as a percent of revenue in fiscal year 2026?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("NVDA", q)
    assert report is None
    assert sources == []
    assert not is_refusal


def test_deterministic_lookup_wrong_year_refusal():
    """Query for year entirely outside filing span (e.g. 2012) must return exact refusal."""
    q = "What was NVIDIA's quarterly dividend in 2012?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("NVDA", q)
    assert report == "Not disclosed in the retrieved filings."
    assert is_refusal is True


def test_deterministic_lookup_explanation_fallback():
    """Explanation queries (why, explain, impact) must fall back to RAG."""
    q = "Why did Apple's net sales grow in fiscal year 2026?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("AAPL", q)
    assert report is None
    assert sources == []
    assert not is_refusal


def test_deterministic_lookup_how_much_is_not_explanation():
    """Queries with 'how much' or 'how many' must NOT be treated as explanations."""
    q = "How much was Microsoft's total revenue in fiscal year 2026?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("MSFT", q)
    assert report is not None
    assert not is_refusal
    assert "$331.84B" in report


def test_deterministic_lookup_missing_year_fallback():
    """Queries without a fiscal year must fall back to RAG path."""
    q = "What is Apple's operating income?"
    report, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup("AAPL", q)
    assert report is None
    assert sources == []
    assert not is_refusal

