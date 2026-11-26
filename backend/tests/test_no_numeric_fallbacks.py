import ast
from pathlib import Path

from app.services.sec_service import format_audited_financial_summary

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_production_code_has_no_financial_fallback_literals():
    """Scans production service code for suspicious hardcoded financial numeric fallbacks."""
    production_files = [
        BACKEND_DIR / "app" / "services" / "sec_service.py",
        BACKEND_DIR / "app" / "services" / "analysis_service.py",
    ]

    suspicious_round_numbers = {
        150000, 100000, 2000, 4500, 3500, 5500, 9000, 10000, 20000,
        150_000, 100_000, 2_000, 4_500, 3_500, 5_500, 9_000, 10_000, 20_000,
    }

    for file_path in production_files:
        assert file_path.exists(), f"Missing production file: {file_path}"
        tree = ast.parse(file_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                val = node.value
                assert val not in suspicious_round_numbers, (
                    f"Found hardcoded financial fallback literal {val} in {file_path.name} at line {node.lineno}"
                )


def test_audited_financial_summary_missing_renders_na():
    """Missing metrics in audited financial summary must strictly render as 'n/a' with no fallback."""
    sparse_metrics = {
        "ticker": "TEST",
        "company_name": "Test Co",
        "accession_number": "0000000000-00-000000",
        "period_end_date": "2026-01-01",
        "fiscal_year": "2026",
    }
    summary = format_audited_financial_summary(sparse_metrics)

    # Every core metric row should render 'n/a'
    for metric_name in [
        "Total Revenue", "Gross Profit", "Operating Income", "Net Income",
        "Operating Cash Flow", "Capital Expenditures", "Free Cash Flow",
        "Total Assets", "Cash & Equivalents", "R&D Expense"
    ]:
        assert f"| **{metric_name}** | n/a |" in summary, (
            f"Expected metric '{metric_name}' to render as 'n/a' when missing, but got:\n{summary}"
        )


def test_free_cash_flow_strictly_requires_both_ocf_and_capex():
    """Free Cash Flow is rendered ONLY when both Operating Cash Flow and Capex are present."""
    base = {
        "ticker": "TEST",
        "company_name": "Test Co",
        "accession_number": "0000000000-00-000000",
        "period_end_date": "2026-01-01",
        "fiscal_year": "2026",
    }

    # Case 1: OCF only -> FCF must be n/a
    m1 = dict(base, operating_cash_flow_raw=100_000_000_000.0, operating_cash_flow_label="$100.00B")
    s1 = format_audited_financial_summary(m1)
    assert "| **Free Cash Flow** | n/a |" in s1

    # Case 2: Capex only -> FCF must be n/a
    m2 = dict(base, capex_raw=10_000_000_000.0, capex_label="$10.00B")
    s2 = format_audited_financial_summary(m2)
    assert "| **Free Cash Flow** | n/a |" in s2

    # Case 3: Both present -> FCF is rendered exactly as OCF - Capex
    m3 = dict(
        base,
        operating_cash_flow_raw=100_000_000_000.0,
        operating_cash_flow_label="$100.00B",
        capex_raw=10_000_000_000.0,
        capex_label="$10.00B",
    )
    s3 = format_audited_financial_summary(m3)
    assert "| **Free Cash Flow** | $90.00B (90,000,000,000 USD)" in s3
    assert "Computed: OperatingCashFlow - Capex" in s3

