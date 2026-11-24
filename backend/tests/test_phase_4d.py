"""Unit tests for Phase 4d: Table conversion, Item 8 to 15 redirect,

derived fact formulas, and generator full-chunk prompt fidelity.
All tests run offline with small in-memory HTML fixtures (no network calls).
"""

from bs4 import BeautifulSoup

from app.schemas.analysis import SourceEvidenceNode
from app.services.analysis_service import AnalysisService
from app.services.sec_service import (
    Form10KParser,
    convert_table_to_structured_text,
    format_verified_facts,
)


def test_table_conversion_currency_and_negatives():
    """Verifies that separate '$' cells and parenthesized negatives are correctly merged and formatted."""
    html_table = """
    <table>
        <tr><th>Line Item</th><th>2026</th><th>2025</th></tr>
        <tr><td>Revenue</td><td>$</td><td>21,383</td><td>$</td><td>4,058</td></tr>
        <tr><td>Operating Loss</td><td>(</td><td>1,250</td><td>)</td><td>(</td><td>450</td><td>)</td></tr>
    </table>
    """
    soup = BeautifulSoup(html_table, "lxml")
    table = soup.find("table")
    result = convert_table_to_structured_text(table, surrounding_text="(in millions)")

    assert "Revenue | FY2026: $21,383 | FY2025: $4,058 (in millions)" in result
    assert "Operating Loss | FY2026: -1,250 | FY2025: -450 (in millions)" in result


def test_table_conversion_em_dash_and_parens_single_cell():
    """Verifies that em-dashes ('—') and single-cell parenthesized negatives '(21,383)' are handled properly."""
    html_table = """
    <table>
        <tr><th>Metric</th><th>FY2026</th><th>FY2025</th></tr>
        <tr><td>Net Tax Expense</td><td>(500)</td><td>—</td></tr>
    </table>
    """
    soup = BeautifulSoup(html_table, "lxml")
    table = soup.find("table")
    result = convert_table_to_structured_text(table)

    assert "Net Tax Expense | FY2026: -500 | FY2025: —" in result


def test_table_conversion_colspan_no_duplicate_labels():
    """Verifies that colspan does not repeat the line-item label across column slots."""
    html_table = """
    <table>
        <tr><th colspan="2">Consolidated Statement</th><th colspan="2">2026</th></tr>
        <tr><td colspan="2">Research and Development</td><td>$</td><td>18,520</td></tr>
    </table>
    """
    soup = BeautifulSoup(html_table, "lxml")
    table = soup.find("table")
    result = convert_table_to_structured_text(table)

    # Should NOT contain 'Research and Development Research and Development'
    assert "Research and Development Research and Development" not in result
    assert "Research and Development | FY2026: $18,520" in result


def test_table_conversion_drop_layout_signature_table():
    """Verifies that layout tables with signatures (/s/) and no financial numbers are dropped."""
    html_table = """
    <table>
        <tr><td>By:</td><td>/s/ Jensen Huang</td><td>Title:</td><td>President and CEO</td></tr>
        <tr><td>Date:</td><td>February 25, 2026</td><td></td><td></td></tr>
    </table>
    """
    soup = BeautifulSoup(html_table, "lxml")
    table = soup.find("table")
    result = convert_table_to_structured_text(table)

    assert result == ""


def test_item8_to_item15_redirect():
    """Verifies that when Item 8 is a short cross-reference (<100 words), financial statements and notes are redirected from Item 15."""
    filing_text = """
    ITEM 1. BUSINESS
    We design accelerated computing platforms.

    ITEM 1A. RISK FACTORS
    We face intense global competition.

    ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS
    Revenue increased 65% year-over-year.

    ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA
    The information required by this Item is set forth in our Consolidated Financial Statements and Notes thereto included in Part IV, Item 15 of this Annual Report.

    ITEM 9. CHANGES IN ACCOUNTANTS
    None.

    ITEM 15. EXHIBITS AND FINANCIAL STATEMENT SCHEDULES
    Report of Independent Registered Public Accounting Firm
    Consolidated Statements of Income
    Revenue: $215,938 million
    Consolidated Balance Sheets
    Total Assets: $206,803 million
    Notes to Consolidated Financial Statements
    Note 1 - Summary of Significant Accounting Policies

    SIGNATURES
    Pursuant to the requirements of Section 13...
    """
    items = Form10KParser.extract_items(filing_text)

    assert "Item 8" in items
    item8_content = items["Item 8"]
    # Must contain both the cross-reference and the redirected financial statements
    assert "The information required by this Item is set forth" in item8_content
    assert "=== FINANCIAL STATEMENTS & NOTES (VIA ITEM 15 REDIRECT) ===" in item8_content
    assert "Consolidated Statements of Income" in item8_content
    assert "Revenue: $215,938 million" in item8_content
    assert "Total Assets: $206,803 million" in item8_content


def test_derived_facts_formulas_and_ratios():
    """Verifies that format_verified_facts displays exact code-computed formulas and percentage point changes."""
    mock_metrics = {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "accession_number": "0001045810-26-000021",
        "period_end_date": "2026-01-25",
        "revenue_label": "$215.94B",
        "revenue_raw": 215938000000.0,
        "revenue_tag": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "margin_label": "71.1%",
        "gross_margin": 71.1,
        "gross_margin_change_label": "-3.9 pp",
        "gross_margin_change_formula": "71.1% - 75.0% = -3.9 pp",
        "operating_margin_label": "60.4%",
        "operating_margin_formula": "$130.39B / $215.94B = 60.4%",
        "operating_margin_change_label": "+13.5 pp",
        "operating_margin_change_formula": "60.4% - 46.9% = +13.5 pp",
        "rd_percent_of_revenue_label": "8.6%",
        "rd_percent_of_revenue_formula": "$18.52B / $215.94B = 8.6%",
        "capex_percent_of_revenue_label": "2.1%",
        "capex_percent_of_revenue_formula": "$4.52B / $215.94B = 2.1%",
    }

    facts_block = format_verified_facts(mock_metrics)

    assert "=== VERIFIED FACTS (SEC EDGAR XBRL) ===" in facts_block
    assert "Derived Financial Metrics & Ratios (Code-Computed with Formulas):" in facts_block
    assert "- Gross Margin Change: -3.9 pp (Formula: 71.1% - 75.0% = -3.9 pp)" in facts_block
    assert "- Operating Margin: 60.4% (Formula: $130.39B / $215.94B = 60.4%)" in facts_block
    assert "- Operating Margin Change: +13.5 pp (Formula: 60.4% - 46.9% = +13.5 pp)" in facts_block
    assert "- R&D as % of Revenue: 8.6% (Formula: $18.52B / $215.94B = 8.6%)" in facts_block
    assert "- Capex as % of Revenue: 2.1% (Formula: $4.52B / $215.94B = 2.1%)" in facts_block


def test_generator_prompt_receives_full_chunk_text():
    """Verifies that _format_source_passage formats the full chunk text (src.text) and not merely the truncated 300-char quote."""
    full_body = (
        "This is an extensive financial discussion from Item 7 MD&A. "
        + "It contains multiple in-depth paragraphs explaining gross margin headwinds, "
        + "supply chain commitments with wafer foundries, and long-term capital expenditure allocations. "
    ) * 10  # > 1500 characters

    node = SourceEvidenceNode(
        source="NVDA_10K.txt",
        section="Item 7",
        quote=full_body[:250],  # truncated quote
        text=full_body,  # full chunk
        score=0.92,
    )

    formatted = AnalysisService._format_source_passage(idx=1, src=node)

    # Must contain full chunk length, far exceeding the 250/300 char quote limit
    assert len(formatted) > 1000
    assert full_body in formatted

