import json
from pathlib import Path

import pytest

from app.api.v1.endpoints.demo import (
    SAMPLE_COMPARISON,
    SAMPLE_COVERAGE,
    SAMPLE_SINGLE_STOCK,
)
from app.core.config import settings
from app.services.article_service import article_service
from app.services.metrics_service import metrics_service
from app.services.sec_service import (
    SECClient,
    XBRLParser,
    validate_user_agent,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "sec"


@pytest.fixture(autouse=True)
def block_all_network(monkeypatch):
    """Enforces zero external network calls in tests."""
    def guarded_get(*args, **kwargs):
        raise RuntimeError("External network call attempted in offline test!")

    import httpx
    monkeypatch.setattr(httpx.Client, "get", guarded_get)


def test_user_agent_missing_fails():
    """Fails with clear error if SEC_EDGAR_USER_AGENT is missing or empty."""
    with pytest.raises(ValueError, match="missing or empty"):
        validate_user_agent(None)

    with pytest.raises(ValueError, match="missing or empty"):
        validate_user_agent("   ")


def test_user_agent_missing_email_fails():
    """Fails with clear error if SEC_EDGAR_USER_AGENT has no valid email address."""
    with pytest.raises(ValueError, match="does not contain a valid contact email"):
        validate_user_agent("ApexEquity Research Admin")

    with pytest.raises(ValueError, match="does not contain a valid contact email"):
        validate_user_agent("MyCompany invalid_email_at_domain.com")


def test_user_agent_valid_succeeds():
    """Succeeds with compliant User-Agent using placeholder email."""
    ua = "ApexEquity Research you@example.com"
    validated = validate_user_agent(ua)
    assert validated == ua


def test_disallowed_host_fails():
    """Validates that network access is restricted only to allowed SEC hosts."""
    client = SECClient()
    with pytest.raises(ValueError, match="Disallowed SEC host"):
        client._validate_host("https://malicious-domain.com/data")


def test_disk_cache_hit_prevents_network(tmp_path):
    """Verifies that an existing cache file on disk is read directly without calling network."""
    cached_file = tmp_path / "test_cached.json"
    test_payload = {"status": "ok", "source": "disk_cache"}
    cached_file.write_text(json.dumps(test_payload), encoding="utf-8")

    client = SECClient(cache_dir=tmp_path)
    # block_all_network fixture is active; reading disk cache will NOT trigger guarded_get
    result = client.get_json("https://data.sec.gov/test", "test_cached.json")
    assert result == test_payload


def test_xbrl_parsing_nvda():
    """Verifies grounded XBRL extraction for NVDA: FY2024, period end 2024-01-28, accession number."""
    parser = XBRLParser()
    facts = json.loads((FIXTURES_DIR / "companyfacts_NVDA.json").read_text(encoding="utf-8"))
    metrics = parser.parse_metrics("NVDA", facts)

    assert metrics["ticker"] == "NVDA"
    assert metrics["source"] == "SEC filing"
    assert metrics["fiscal_year"] == 2024
    assert metrics["period_end_date"] == "2024-01-28"
    assert metrics["accession_number"] == "0001045810-24-000029"
    assert metrics["revenue"] == 60.92
    assert metrics["revenue_label"] == "$60.92B"
    assert "2024-01-28" in metrics["revenue_period"]
    assert metrics["gross_margin"] == 72.7
    assert metrics["growth_yoy"] == 125.9


def test_xbrl_parsing_msft():
    """Verifies grounded XBRL extraction for MSFT: FY2024, period end 2024-06-30."""
    parser = XBRLParser()
    facts = json.loads((FIXTURES_DIR / "companyfacts_MSFT.json").read_text(encoding="utf-8"))
    metrics = parser.parse_metrics("MSFT", facts)

    assert metrics["ticker"] == "MSFT"
    assert metrics["fiscal_year"] == 2024
    assert metrics["period_end_date"] == "2024-06-30"
    assert metrics["accession_number"] == "0000789019-24-000074"
    assert metrics["revenue"] == 245.12
    assert metrics["gross_margin"] == 69.8
    assert metrics["growth_yoy"] == 15.7


def test_xbrl_parsing_aapl():
    """Verifies grounded XBRL extraction for AAPL: FY2024, period end 2024-09-28."""
    parser = XBRLParser()
    facts = json.loads((FIXTURES_DIR / "companyfacts_AAPL.json").read_text(encoding="utf-8"))
    metrics = parser.parse_metrics("AAPL", facts)

    assert metrics["ticker"] == "AAPL"
    assert metrics["fiscal_year"] == 2024
    assert metrics["period_end_date"] == "2024-09-28"
    assert metrics["accession_number"] == "0000320193-24-000106"
    assert metrics["revenue"] == 391.04
    assert metrics["gross_margin"] == 46.2
    assert metrics["growth_yoy"] == 2.0


def test_xbrl_parsing_googl_without_gross_profit_tag():
    """Verifies Condition 8: GOOGL has no GrossProfit tag, gross margin computed as (Revenue - CostOfRevenue) / Revenue."""
    parser = XBRLParser()
    facts = json.loads((FIXTURES_DIR / "companyfacts_GOOGL.json").read_text(encoding="utf-8"))
    metrics = parser.parse_metrics("GOOGL", facts)

    assert metrics["ticker"] == "GOOGL"
    assert metrics["fiscal_year"] == 2023
    assert metrics["period_end_date"] == "2023-12-31"
    assert metrics["accession_number"] == "0001652044-24-000019"
    assert metrics["revenue"] == 307.39
    # Computed: (307394000000 - 133332000000) / 307394000000 * 100 = 56.6%
    assert metrics["gross_margin"] == 56.6
    assert "Computed" in metrics["margin_tag"]
    assert metrics["cost_tag"] == "CostOfRevenue"


def test_xbrl_parsing_amd():
    """Verifies grounded XBRL extraction for AMD: FY2023, period end 2023-12-30."""
    parser = XBRLParser()
    facts = json.loads((FIXTURES_DIR / "companyfacts_AMD.json").read_text(encoding="utf-8"))
    metrics = parser.parse_metrics("AMD", facts)

    assert metrics["ticker"] == "AMD"
    assert metrics["fiscal_year"] == 2023
    assert metrics["period_end_date"] == "2023-12-30"
    assert metrics["accession_number"] == "0000002488-24-000012"
    assert metrics["revenue"] == 22.68
    assert metrics["gross_margin"] == 46.1


def test_metrics_service_truthful_document_labeling(tmp_path, monkeypatch):
    """Tests Requirement 4:

    - SEC filing only when from SEC EDGAR
    - Yahoo Finance snapshot (undated) only when from undated snapshot
    - Hand-written summary otherwise
    - Never defaults to Yahoo Finance snapshot
    """
    monkeypatch.setattr(settings, "ARTICLES_DIR", tmp_path)
    monkeypatch.setattr(metrics_service, "_cache", {})

    # 1. Hand-written summary
    (tmp_path / "CUSTOM.txt").write_text(
        "CUSTOM Corp reported quarterly revenue of $10.0 billion, up 20% YoY. Gross margin 50%.",
        encoding="utf-8",
    )
    m_custom = metrics_service._parse_from_ingested_file("CUSTOM")
    assert m_custom["source"] == "Hand-written summary"
    assert m_custom["source_badge"] == "From hand-written summary"

    # 2. Undated Yahoo snapshot
    (tmp_path / "AMD_TEST.txt").write_text(
        "[DOCUMENT_SOURCE: Yahoo Finance snapshot (undated)]\n"
        "Advanced Micro Devices Financial & Corporate Overview\n"
        "Total Revenue (TTM): $22.68 Billion\nGross Margin: 46.0%",
        encoding="utf-8",
    )
    m_amd = metrics_service._parse_from_ingested_file("AMD_TEST")
    assert m_amd["source"] == "Yahoo Finance snapshot (undated)"

    # 3. SEC filing
    (tmp_path / "NVDA_TEST_10K.txt").write_text(
        "[DOCUMENT_METADATA]\n"
        "Document Type: SEC filing\n"
        "Source: SEC EDGAR\n"
        "Ticker: NVDA_TEST\n"
        "Fiscal Year: 2024\n"
        "Period End Date: 2024-01-28\n"
        "Accession Number: 0001045810-24-000029\n"
        "Total Revenue: $60.92B (FY 2024 (ended 2024-01-28))\n"
        "Gross Margin: 72.7% (FY 2024 (ended 2024-01-28))\n"
        "[/DOCUMENT_METADATA]\n\n"
        "=== ITEM 1. BUSINESS ===\nSample business.",
        encoding="utf-8",
    )
    m_sec = metrics_service._parse_from_ingested_file("NVDA_TEST")
    assert m_sec["source"] == "SEC filing"
    assert m_sec["accession_number"] == "0001045810-24-000029"
    assert m_sec["period_end_date"] == "2024-01-28"

    # 4. Fallback for non-existent stock: never defaults to Yahoo Finance snapshot
    monkeypatch.setattr(metrics_service, "_fetch_from_yfinance", lambda t: None)
    m_missing = metrics_service.get_metrics("NONEXISTENT")
    assert m_missing["source"] is None
    assert m_missing["source_label"] == "Unknown"
    assert "Yahoo" not in str(m_missing["source_badge"])


def test_article_service_excludes_amd_snapshot_when_10k_exists(tmp_path, monkeypatch):
    """Verifies Condition 4: When AMD_10K.txt exists, AMD.txt is excluded from vector indexing."""
    monkeypatch.setattr(settings, "ARTICLES_DIR", tmp_path)

    (tmp_path / "AMD.txt").write_text("Undated snapshot content", encoding="utf-8")
    (tmp_path / "AMD_10K.txt").write_text("Official 10-K filing content", encoding="utf-8")
    (tmp_path / "NVDA_10K.txt").write_text("Official NVDA 10-K filing content", encoding="utf-8")

    indexable = article_service._get_indexable_files()
    indexable_names = [p.name for p in indexable]

    assert "AMD_10K.txt" in indexable_names
    assert "NVDA_10K.txt" in indexable_names
    assert "AMD.txt" not in indexable_names  # Excluded from index!
    assert (tmp_path / "AMD.txt").exists()  # Retained on disk!


def test_demo_sample_card_truthfulness():
    """Verifies Condition 6:

    Demo cards must not carry a real source label (Yahoo Finance snapshot) or guessed periods (Q4/Q2/Q1).
    Must state 'Illustrative sample, not from a document' and note old 2023-24 era figures.
    """
    assert "2023-24" in SAMPLE_SINGLE_STOCK["sample_notice"]
    assert SAMPLE_SINGLE_STOCK["metrics"]["source_label"] == "Illustrative sample, not from a document"
    assert SAMPLE_SINGLE_STOCK["metrics"]["revenue_source"] == "Illustrative sample, not from a document"
    assert SAMPLE_SINGLE_STOCK["metrics"]["revenue_period"] == "Illustrative sample, not from a document"

    for item in SAMPLE_COMPARISON["comparison_metrics"]:
        assert item["source"] == "Illustrative sample, not from a document"
        assert item["period"] == "Illustrative sample, not from a document"

    for comp in SAMPLE_COVERAGE["companies"]:
        assert comp["source"] == "Illustrative sample, not from a document"
        assert comp["period"] == "Illustrative sample, not from a document"
        assert "2023-24" in comp["badge"]
