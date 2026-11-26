import json
from pathlib import Path

import pytest
from app.services.sec_service import XBRLParser

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "trimmed_companyfacts"

EXPECTED_LATEST = {
    "NVDA": {
        "period_end": "2026-01-25",
        "revenue_raw": 215938000000.0,
        "operating_income_raw": 130387000000.0,
        "net_income_raw": 120067000000.0,
        "total_assets_raw": 206803000000.0,
        "operating_cash_flow_raw": 102718000000.0,
        "capex_raw": 6042000000.0,
        "prior_revenue_raw": 130497000000.0,
    },
    "MSFT": {
        "period_end": "2026-06-30",
        "revenue_raw": 331839000000.0,
        "operating_income_raw": 155237000000.0,
        "net_income_raw": 133749000000.0,
        "total_assets_raw": 758376000000.0,
        "operating_cash_flow_raw": 182935000000.0,
        "capex_raw": 115948000000.0,
        "prior_revenue_raw": 281724000000.0,
    },
    "AAPL": {
        "period_end": "2026-09-26",
        "revenue_raw": 478834000000.0,
        "operating_income_raw": 158063000000.0,
        "net_income_raw": 132175000000.0,
        "total_assets_raw": 404548000000.0,
        "operating_cash_flow_raw": 145097000000.0,
        "capex_raw": 9041000000.0,
        "prior_revenue_raw": 416161000000.0,
    },
    "GOOGL": {
        "period_end": "2025-12-31",
        "revenue_raw": 402836000000.0,
        "operating_income_raw": 129039000000.0,
        "net_income_raw": 132170000000.0,
        "total_assets_raw": 595281000000.0,
        "operating_cash_flow_raw": 164713000000.0,
        "capex_raw": 91447000000.0,
        "prior_revenue_raw": 350018000000.0,
    },
    "AMD": {
        "period_end": "2025-12-27",
        "revenue_raw": 34639000000.0,
        "operating_income_raw": 3694000000.0,
        "net_income_raw": 4335000000.0,
        "total_assets_raw": 76926000000.0,
        "operating_cash_flow_raw": 7709000000.0,
        "capex_raw": 974000000.0,
        "prior_revenue_raw": 25785000000.0,
    },
}


@pytest.mark.parametrize("ticker", ["NVDA", "MSFT", "AAPL", "GOOGL", "AMD"])
def test_xbrl_parser_selects_latest_annual_facts(ticker: str):
    fixture_path = FIXTURES_DIR / f"companyfacts_{ticker}.json"
    assert fixture_path.exists(), f"Missing fixture {fixture_path}"

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    parser = XBRLParser()
    metrics = parser.parse_metrics(ticker, data)

    expected = EXPECTED_LATEST[ticker]
    assert metrics["period_end_date"] == expected["period_end"]
    assert metrics["revenue_raw"] == expected["revenue_raw"]
    assert metrics["operating_income_raw"] == expected["operating_income_raw"]
    assert metrics["net_income_raw"] == expected["net_income_raw"]
    assert metrics["total_assets_raw"] == expected["total_assets_raw"]
    assert metrics["operating_cash_flow_raw"] == expected["operating_cash_flow_raw"]
    assert metrics["capex_raw"] == expected["capex_raw"]
    assert metrics["prior_revenue_raw"] == expected["prior_revenue_raw"]


@pytest.mark.parametrize("ticker", ["NVDA", "MSFT", "AAPL", "GOOGL", "AMD"])
def test_fails_if_prior_year_value_is_chosen_as_latest(ticker: str):
    fixture_path = FIXTURES_DIR / f"companyfacts_{ticker}.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    parser = XBRLParser()
    metrics = parser.parse_metrics(ticker, data)

    expected = EXPECTED_LATEST[ticker]
    # Asserting that the latest revenue equals the prior year revenue MUST fail
    with pytest.raises(AssertionError):
        assert metrics["revenue_raw"] == expected["prior_revenue_raw"]

