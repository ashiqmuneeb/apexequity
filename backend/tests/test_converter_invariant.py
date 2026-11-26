from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.services.sec_service import convert_table_to_structured_text


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_nvda_income_statement_real_fixture():
    f_path = FIXTURES_DIR / "nvda_income_statement.html"
    assert f_path.exists(), f"Missing fixture {f_path}"
    soup = BeautifulSoup(f_path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table")
    text = convert_table_to_structured_text(table)
    lines = [line for line in text.splitlines() if line.strip()]

    # First data row is Revenue
    rev_line = [line for line in lines if line.startswith("Revenue |")][0]
    parts = [p.strip() for p in rev_line.split("|")]

    # First value column must carry latest period and exact value
    col1 = parts[1]
    assert "FY2026" in col1
    assert "2026-01-25" in col1
    assert "$215,938" in col1

    # Second column is prior year FY2025
    col2 = parts[2]
    assert "FY2025" in col2
    assert "2025-01-26" in col2
    assert "$130,497" in col2


def test_msft_income_statement_real_fixture():
    f_path = FIXTURES_DIR / "msft_income_statement.html"
    assert f_path.exists(), f"Missing fixture {f_path}"
    soup = BeautifulSoup(f_path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table")
    text = convert_table_to_structured_text(table)
    lines = [line for line in text.splitlines() if line.strip()]

    rev_line = [line for line in lines if line.startswith("Total revenue |")][0]
    parts = [p.strip() for p in rev_line.split("|")]

    col1 = parts[1]
    assert "FY2026" in col1
    assert "2026-06-30" in col1
    assert "331,839" in col1


def test_aapl_income_statement_real_fixture():
    f_path = FIXTURES_DIR / "aapl_income_statement.html"
    assert f_path.exists(), f"Missing fixture {f_path}"
    soup = BeautifulSoup(f_path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table")
    text = convert_table_to_structured_text(table)
    lines = [line for line in text.splitlines() if line.strip()]

    sales_line = [line for line in lines if line.startswith("Total net sales |")][0]
    parts = [p.strip() for p in sales_line.split("|")]

    col1 = parts[1]
    assert "FY2026" in col1
    assert "2026-09-26" in col1
    assert "478,834" in col1


def test_googl_income_statement_real_fixture_ascending_reversal():
    f_path = FIXTURES_DIR / "googl_income_statement.html"
    assert f_path.exists(), f"Missing fixture {f_path}"
    soup = BeautifulSoup(f_path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table")
    text = convert_table_to_structured_text(table)
    lines = [line for line in text.splitlines() if line.strip()]

    rev_line = [line for line in lines if line.startswith("Revenues |")][0]
    parts = [p.strip() for p in rev_line.split("|")]

    # In ascending table (2023, 2024, 2025), Col 1 must be reversed to latest period FY2025
    col1 = parts[1]
    assert "FY2025" in col1
    assert "2025-12-31" in col1
    assert "$402,836" in col1

    col2 = parts[2]
    assert "FY2024" in col2
    assert "2024-12-31" in col2
    assert "$350,018" in col2

    col3 = parts[3]
    assert "FY2023" in col3
    assert "2023-12-31" in col3
    assert "$307,394" in col3


def test_amd_income_statement_real_fixture():
    f_path = FIXTURES_DIR / "amd_income_statement.html"
    assert f_path.exists(), f"Missing fixture {f_path}"
    soup = BeautifulSoup(f_path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table")
    text = convert_table_to_structured_text(table)
    lines = [line for line in text.splitlines() if line.strip()]

    rev_line = [line for line in lines if line.startswith("Net revenue |")][0]
    parts = [p.strip() for p in rev_line.split("|")]

    col1 = parts[1]
    assert "FY2025" in col1
    assert "2025-12-27" in col1
    assert "$34,639" in col1


def test_layout_table_neutralization():
    f_path = FIXTURES_DIR / "aapl_toc_layout.html"
    assert f_path.exists(), f"Missing fixture {f_path}"
    soup = BeautifulSoup(f_path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table")
    text = convert_table_to_structured_text(table)
    assert text == "", "TOC layout table should produce empty string"


def test_invariant_fails_on_dropped_or_shifted_columns():
    # If Col 1 had FY2025 instead of FY2026 for NVDA, invariant must fail
    f_path = FIXTURES_DIR / "nvda_income_statement.html"
    soup = BeautifulSoup(f_path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table")
    text = convert_table_to_structured_text(table)
    lines = [line for line in text.splitlines() if line.strip()]
    parts = [p.strip() for p in lines[0].split("|")]

    with pytest.raises(AssertionError):
        # Asserting wrong year fails
        assert "FY2025" in parts[1]


def test_aapl_mda_table_with_percent_merging():
    html = """
    <table>
      <tr><td></td><td>2026</td><td>Change</td><td>2025</td><td>Change</td><td>2024</td></tr>
      <tr><td>Total net sales</td><td>$</td><td>478,834</td><td>15</td><td>%</td><td>$</td><td>416,161</td><td>6</td><td>%</td><td>$</td><td>391,035</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    converted = convert_table_to_structured_text(soup.find("table"))
    assert "15%" in converted
    assert "6%" in converted
    # Period header FY2026 must attach to $478,834, not 15%
    assert "FY2026: $478,834" in converted
    assert "Change: 15%" in converted


def test_googl_mda_table_with_change_columns_no_reversal():
    html = """
    <table>
      <tr><td>Year Ended December 31,</td></tr>
      <tr><td></td><td>2024</td><td>2025</td><td>$ Change</td><td>% Change</td></tr>
      <tr><td>Consolidated revenues</td><td>$</td><td>350,018</td><td>$</td><td>402,836</td><td>$</td><td>52,818</td><td>15</td><td>%</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    converted = convert_table_to_structured_text(soup.find("table"))
    assert "FY2024 (2024-12-31): $350,018" in converted
    assert "FY2025 (2025-12-31): $402,836" in converted
    assert "$ Change: $52,818" in converted
    assert "% Change: 15%" in converted


def test_nvda_mda_table_with_separate_percent_cells():
    html = """
    <table>
      <tr><td>Year Ended</td></tr>
      <tr><td></td><td>Jan 25, 2026</td><td>Jan 26, 2025</td></tr>
      <tr><td>Revenue</td><td>100.0</td><td>%</td><td>100.0</td><td>%</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    converted = convert_table_to_structured_text(soup.find("table"))
    assert "FY2026 (2026-01-25): 100.0%" in converted
    assert "FY2025 (2025-01-26): 100.0%" in converted


def test_unaligned_table_emission():
    html = """
    <table>
      <tr><td></td><td>2026</td><td>2025</td></tr>
      <tr><td>Odd Row Item</td><td>123</td><td>456</td><td>789</td><td>Extra</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    converted = convert_table_to_structured_text(soup.find("table"))
    assert "[unaligned]" in converted

