import json
import os
import re
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from app.core.config import settings
from app.core.logger import logger


warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

ALLOWED_SEC_HOSTS = {"data.sec.gov", "www.sec.gov"}

# Target companies
TARGET_COMPANIES = {
    "NVDA": {"cik": "0001045810", "name": "NVIDIA CORP"},
    "MSFT": {"cik": "0000789019", "name": "MICROSOFT CORP"},
    "AAPL": {"cik": "0000320193", "name": "APPLE INC"},
    "GOOGL": {"cik": "0001652044", "name": "ALPHABET INC"},
    "AMD": {"cik": "0000002488", "name": "ADVANCED MICRO DEVICES INC"},
}

REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
]

GROSS_PROFIT_TAGS = [
    "GrossProfit",
]

COST_OF_REVENUE_TAGS = [
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "CostOfGoodsSold",
]

OPERATING_INCOME_TAGS = [
    "OperatingIncomeLoss",
]

NET_INCOME_TAGS = [
    "NetIncomeLoss",
    "ProfitLoss",
]

RD_EXPENSE_TAGS = [
    "ResearchAndDevelopmentExpense",
    "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
]

CASH_AND_EQUIV_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]

CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
]

ASSETS_TAGS = [
    "Assets",
]

OPERATING_CASH_FLOW_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
]


def validate_user_agent(user_agent: str | None) -> str:
    """Validates SEC EDGAR User-Agent according to SEC policy.

    Must come from SEC_EDGAR_USER_AGENT, never a fake default.
    Must contain a valid contact email address.
    """
    if not user_agent or not user_agent.strip():
        raise ValueError(
            "SEC_EDGAR_USER_AGENT environment variable is missing or empty. "
            "SEC EDGAR mandates a User-Agent in the format 'Sample Company Name AdminContact@domain.com'. "
            "Please configure it in backend/.env."
        )

    clean_ua = user_agent.strip()
    if not EMAIL_REGEX.search(clean_ua):
        raise ValueError(
            f"SEC_EDGAR_USER_AGENT ('{clean_ua}') does not contain a valid contact email address. "
            "SEC EDGAR mandates a User-Agent in the format 'Sample Company Name AdminContact@domain.com'."
        )

    return clean_ua


class SECClient:
    """HTTP Client for SEC EDGAR APIs with disk caching and rate limiting.

    Only communicates with data.sec.gov and www.sec.gov.
    """

    def __init__(self, cache_dir: Path | None = None, min_request_interval: float = 0.25):
        self.cache_dir = cache_dir or settings.SEC_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_request_interval = min_request_interval
        self._last_request_time = 0.0

    def _get_user_agent(self) -> str:
        ua = settings.SEC_EDGAR_USER_AGENT or os.getenv("SEC_EDGAR_USER_AGENT")
        return validate_user_agent(ua)

    def _validate_host(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.netloc not in ALLOWED_SEC_HOSTS:
            raise ValueError(
                f"Disallowed SEC host '{parsed.netloc}'. "
                f"Network access is strictly limited to: {', '.join(sorted(ALLOWED_SEC_HOSTS))}."
            )

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, cache_filename: str) -> str:
        """Fetches from disk cache if present, otherwise fetches from SEC EDGAR and caches to disk."""
        self._validate_host(url)
        cache_path = self.cache_dir / cache_filename

        if cache_path.exists() and cache_path.stat().st_size > 0:
            logger.info(f"SEC Cache hit: {cache_filename}")
            return cache_path.read_text(encoding="utf-8")

        ua = self._get_user_agent()
        self._rate_limit()

        logger.info(f"Fetching from SEC EDGAR: {url}")
        headers = {
            "User-Agent": ua,
            "Accept-Encoding": "gzip, deflate",
        }

        with httpx.Client(timeout=45.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"SEC EDGAR request failed [{resp.status_code}] for {url}: {resp.text[:300]}"
                )
            content = resp.text
            cache_path.write_text(content, encoding="utf-8")
            logger.info(f"Cached SEC response: {cache_filename} ({len(content)} chars)")
            return content

    def get_json(self, url: str, cache_filename: str) -> dict[str, Any]:
        """Fetches and caches JSON from SEC EDGAR."""
        text = self.get(url, cache_filename)
        return json.loads(text)

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        """Fetches XBRL company facts for a CIK."""
        padded_cik = str(cik).zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
        return self.get_json(url, f"companyfacts_{padded_cik}.json")

    def get_submissions(self, cik: str) -> dict[str, Any]:
        """Fetches submission history for a CIK."""
        padded_cik = str(cik).zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
        return self.get_json(url, f"submissions_{padded_cik}.json")

    def get_filing_document(self, cik: str, accession_number: str, primary_doc: str) -> str:
        """Fetches primary filing document text or HTML from SEC archives."""
        cik_clean = str(int(cik))
        accn_no_hyphen = accession_number.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accn_no_hyphen}/{primary_doc}"
        safe_name = f"filing_{cik_clean}_{accn_no_hyphen}_{Path(primary_doc).name}"
        return self.get(url, safe_name)


def format_verified_facts(metrics: dict[str, Any]) -> str:
    """Formats structured SEC XBRL facts into a VERIFIED FACTS prompt context block."""
    ticker = metrics.get("ticker", "UNKNOWN")
    company = metrics.get("company_name") or ticker
    accn = metrics.get("accession_number", "N/A")
    period_end = metrics.get("period_end_date", "N/A")

    lines = [
        "=== VERIFIED FACTS (SEC EDGAR XBRL) ===",
        f"Company: {company} ({ticker})",
        f"Primary Accession Number: {accn}",
        "",
        f"Current Period (ended {period_end}):",
        f"- Revenue: {metrics.get('revenue_label', 'N/A')} ({metrics.get('revenue_raw', 0):,.0f} USD) [Tag: {metrics.get('revenue_tag', 'N/A')}]",
    ]

    if metrics.get("gross_profit_label") is not None:
        lines.append(
            f"- Gross Profit: {metrics.get('gross_profit_label')} ({metrics.get('gross_profit_raw', 0):,.0f} USD) [Tag: {metrics.get('gross_profit_tag', 'N/A')}]"
        )
    if metrics.get("cost_label") is not None:
        lines.append(
            f"- Cost of Revenue: {metrics.get('cost_label')} ({metrics.get('cost_raw', 0):,.0f} USD) [Tag: {metrics.get('cost_tag', 'N/A')}]"
        )
    lines.append(
        f"- Gross Margin: {metrics.get('margin_label', 'N/A')} [Tag: {metrics.get('margin_tag', 'N/A')}]"
    )
    if metrics.get("growth_label") is not None:
        lines.append(
            f"- YoY Revenue Growth: {metrics.get('growth_label')} ({metrics.get('growth_period', 'N/A')})"
        )
    if metrics.get("operating_income_label") is not None:
        lines.append(
            f"- Operating Income: {metrics.get('operating_income_label')} ({metrics.get('operating_income_raw', 0):,.0f} USD) [Tag: {metrics.get('operating_income_tag', 'N/A')}]"
        )
    if metrics.get("net_income_label") is not None:
        lines.append(
            f"- Net Income: {metrics.get('net_income_label')} ({metrics.get('net_income_raw', 0):,.0f} USD) [Tag: {metrics.get('net_income_tag', 'N/A')}]"
        )
    if metrics.get("rd_expense_label") is not None:
        lines.append(
            f"- R&D Expense: {metrics.get('rd_expense_label')} ({metrics.get('rd_expense_raw', 0):,.0f} USD) [Tag: {metrics.get('rd_expense_tag', 'N/A')}]"
        )
    if metrics.get("cash_and_equiv_label") is not None:
        lines.append(
            f"- Cash & Cash Equivalents: {metrics.get('cash_and_equiv_label')} ({metrics.get('cash_and_equiv_raw', 0):,.0f} USD) [Tag: {metrics.get('cash_and_equiv_tag', 'N/A')}]"
        )
    if metrics.get("capex_label") is not None:
        lines.append(
            f"- Capital Expenditures: {metrics.get('capex_label')} ({metrics.get('capex_raw', 0):,.0f} USD) [Tag: {metrics.get('capex_tag', 'N/A')}]"
        )

    # Prior Period
    prior_end = metrics.get("prior_period_end_date")
    if prior_end:
        prior_accn = metrics.get("prior_accession_number") or accn
        lines.extend([
            "",
            f"Prior Period (ended {prior_end}) [Accession: {prior_accn}]:",
            f"- Prior Revenue: {metrics.get('prior_revenue_label', 'N/A')} ({metrics.get('prior_revenue_raw', 0):,.0f} USD) [Tag: {metrics.get('revenue_tag', 'N/A')}]",
        ])
        if metrics.get("prior_gross_profit_label") is not None:
            lines.append(
                f"- Prior Gross Profit: {metrics.get('prior_gross_profit_label')} ({metrics.get('prior_gross_profit_raw', 0):,.0f} USD) [Tag: {metrics.get('gross_profit_tag', 'N/A')}]"
            )
        if metrics.get("prior_cost_label") is not None:
            lines.append(
                f"- Prior Cost of Revenue: {metrics.get('prior_cost_label')} ({metrics.get('prior_cost_raw', 0):,.0f} USD) [Tag: {metrics.get('cost_tag', 'N/A')}]"
            )
        if metrics.get("prior_margin_label") is not None:
            lines.append(
                f"- Prior Gross Margin: {metrics.get('prior_margin_label')}"
            )
        if metrics.get("prior_operating_income_label") is not None:
            lines.append(
                f"- Prior Operating Income: {metrics.get('prior_operating_income_label')} ({metrics.get('prior_operating_income_raw', 0):,.0f} USD) [Tag: {metrics.get('operating_income_tag', 'N/A')}]"
            )
        if metrics.get("prior_net_income_label") is not None:
            lines.append(
                f"- Prior Net Income: {metrics.get('prior_net_income_label')} ({metrics.get('prior_net_income_raw', 0):,.0f} USD) [Tag: {metrics.get('net_income_tag', 'N/A')}]"
            )
        if metrics.get("prior_rd_expense_label") is not None:
            lines.append(
                f"- Prior R&D Expense: {metrics.get('prior_rd_expense_label')} ({metrics.get('prior_rd_expense_raw', 0):,.0f} USD) [Tag: {metrics.get('rd_expense_tag', 'N/A')}]"
            )
        if metrics.get("prior_cash_and_equiv_label") is not None:
            lines.append(
                f"- Prior Cash & Cash Equivalents: {metrics.get('prior_cash_and_equiv_label')} ({metrics.get('prior_cash_and_equiv_raw', 0):,.0f} USD) [Tag: {metrics.get('cash_and_equiv_tag', 'N/A')}]"
            )
        if metrics.get("prior_capex_label") is not None:
            lines.append(
                f"- Prior Capital Expenditures: {metrics.get('prior_capex_label')} ({metrics.get('prior_capex_raw', 0):,.0f} USD) [Tag: {metrics.get('capex_tag', 'N/A')}]"
            )

    # Derived Financial Metrics & Ratios (Code-computed with formulas)
    has_derived = any(
        metrics.get(k) is not None
        for k in [
            "gross_margin_change_label",
            "operating_margin_label",
            "operating_margin_change_label",
            "net_margin_label",
            "net_margin_change_label",
            "opinc_growth_label",
            "net_income_growth_label",
            "rd_growth_label",
            "capex_growth_label",
            "rd_percent_of_revenue_label",
            "capex_percent_of_revenue_label",
            "cost_percent_of_revenue_label",
        ]
    )
    if has_derived:
        lines.extend([
            "",
            "Derived Financial Metrics & Ratios (Code-Computed with Formulas):",
        ])
        if metrics.get("gross_margin_change_label") is not None:
            lines.append(
                f"- Gross Margin Change: {metrics.get('gross_margin_change_label')} (Formula: {metrics.get('gross_margin_change_formula')})"
            )
        if metrics.get("operating_margin_label") is not None:
            lines.append(
                f"- Operating Margin: {metrics.get('operating_margin_label')} (Formula: {metrics.get('operating_margin_formula')})"
            )
        if metrics.get("operating_margin_change_label") is not None:
            lines.append(
                f"- Operating Margin Change: {metrics.get('operating_margin_change_label')} (Formula: {metrics.get('operating_margin_change_formula')})"
            )
        if metrics.get("net_margin_label") is not None:
            lines.append(
                f"- Net Margin: {metrics.get('net_margin_label')} (Formula: {metrics.get('net_margin_formula')})"
            )
        if metrics.get("net_margin_change_label") is not None:
            lines.append(
                f"- Net Margin Change: {metrics.get('net_margin_change_label')} (Formula: {metrics.get('net_margin_change_formula')})"
            )
        if metrics.get("opinc_growth_label") is not None:
            lines.append(
                f"- YoY Operating Income Growth: {metrics.get('opinc_growth_label')} (Formula: {metrics.get('opinc_growth_formula')})"
            )
        if metrics.get("net_income_growth_label") is not None:
            lines.append(
                f"- YoY Net Income Growth: {metrics.get('net_income_growth_label')} (Formula: {metrics.get('net_income_growth_formula')})"
            )
        if metrics.get("rd_growth_label") is not None:
            lines.append(
                f"- YoY R&D Expense Growth: {metrics.get('rd_growth_label')} (Formula: {metrics.get('rd_growth_formula')})"
            )
        if metrics.get("capex_growth_label") is not None:
            lines.append(
                f"- YoY Capital Expenditures Growth: {metrics.get('capex_growth_label')} (Formula: {metrics.get('capex_growth_formula')})"
            )
        if metrics.get("rd_percent_of_revenue_label") is not None:
            lines.append(
                f"- R&D as % of Revenue: {metrics.get('rd_percent_of_revenue_label')} (Formula: {metrics.get('rd_percent_of_revenue_formula')})"
            )
        if metrics.get("capex_percent_of_revenue_label") is not None:
            lines.append(
                f"- Capex as % of Revenue: {metrics.get('capex_percent_of_revenue_label')} (Formula: {metrics.get('capex_percent_of_revenue_formula')})"
            )
        if metrics.get("cost_percent_of_revenue_label") is not None:
            lines.append(
                f"- Cost of Revenue as % of Revenue: {metrics.get('cost_percent_of_revenue_label')} (Formula: {metrics.get('cost_percent_of_revenue_formula')})"
            )

    lines.append("=== END VERIFIED FACTS ===")
    return "\n".join(lines)


def format_audited_financial_summary(metrics: dict[str, Any]) -> str:
    """Renders the institutional Audited Financial Summary of the dossier in code from structured XBRL facts.

    All metrics, tags, dates, and accessions are rendered with zero default/fallback numbers.
    Missing values render strictly as 'n/a'.
    Free Cash Flow is rendered ONLY if both Operating Cash Flow and Capex are present.
    """
    ticker = metrics.get("ticker") or "UNKNOWN"
    company = metrics.get("company_name") or ticker
    accn = metrics.get("accession_number") or "n/a"
    period_end = metrics.get("period_end_date") or "n/a"
    fy = metrics.get("fiscal_year") or "n/a"

    def _fmt_row(
        name: str,
        val_label: str | None,
        raw_val: float | None,
        period: str | None,
        row_accn: str | None,
        tag: str | None,
    ) -> str:
        if val_label is not None and val_label != "n/a" and raw_val is not None:
            val_str = f"{val_label} ({raw_val:,.0f} USD)"
        elif val_label is not None and val_label != "n/a":
            val_str = str(val_label)
        else:
            val_str = "n/a"

        p_str = period if (period and period != "n/a") else period_end
        a_str = row_accn if (row_accn and row_accn != "n/a") else accn
        t_str = f"`{tag}`" if (tag and tag != "n/a") else "n/a"
        if val_str == "n/a":
            p_str = "n/a"
            a_str = "n/a"
            t_str = "n/a"
        return f"| **{name}** | {val_str} | {p_str} | {a_str} | {t_str} |"

    out = [
        f"### Audited Financial Summary: {company} ({ticker})",
        f"**Source:** SEC EDGAR Form 10-K | **Fiscal Year:** FY{fy} (ended {period_end}) | **Accession Number:** {accn}",
        "",
        "| Financial Metric | Reported Value | Fiscal Period | Accession Number | GAAP Concept Tag |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    out.append(_fmt_row("Total Revenue", metrics.get("revenue_label"), metrics.get("revenue_raw"), metrics.get("period_end_date"), metrics.get("accession_number"), metrics.get("revenue_tag")))
    out.append(_fmt_row("Gross Profit", metrics.get("gross_profit_label"), metrics.get("gross_profit_raw"), metrics.get("period_end_date"), metrics.get("accession_number"), metrics.get("gross_profit_tag")))
    out.append(_fmt_row("Gross Margin", metrics.get("margin_label"), None, metrics.get("period_end_date"), metrics.get("accession_number"), metrics.get("margin_tag") or "Computed: GrossProfit / Revenues"))
    out.append(_fmt_row("Operating Income", metrics.get("operating_income_label"), metrics.get("operating_income_raw"), metrics.get("operating_income_period") or metrics.get("period_end_date"), metrics.get("operating_income_accession") or metrics.get("accession_number"), metrics.get("operating_income_tag")))
    out.append(_fmt_row("Operating Margin", metrics.get("operating_margin_label"), None, metrics.get("period_end_date"), metrics.get("accession_number"), "Computed: OperatingIncome / Revenues"))
    out.append(_fmt_row("Net Income", metrics.get("net_income_label"), metrics.get("net_income_raw"), metrics.get("net_income_period") or metrics.get("period_end_date"), metrics.get("net_income_accession") or metrics.get("accession_number"), metrics.get("net_income_tag")))
    out.append(_fmt_row("Net Margin", metrics.get("net_margin_label"), None, metrics.get("period_end_date"), metrics.get("accession_number"), "Computed: NetIncome / Revenues"))
    out.append(_fmt_row("Operating Cash Flow", metrics.get("operating_cash_flow_label"), metrics.get("operating_cash_flow_raw"), metrics.get("operating_cash_flow_period") or metrics.get("period_end_date"), metrics.get("operating_cash_flow_accession") or metrics.get("accession_number"), metrics.get("operating_cash_flow_tag")))
    out.append(_fmt_row("Capital Expenditures", metrics.get("capex_label"), metrics.get("capex_raw"), metrics.get("capex_period") or metrics.get("period_end_date"), metrics.get("capex_accession") or metrics.get("accession_number"), metrics.get("capex_tag")))

    # Free Cash Flow: only if both operating cash flow and capex are present
    ocf_raw = metrics.get("operating_cash_flow_raw")
    capex_raw = metrics.get("capex_raw")
    if ocf_raw is not None and capex_raw is not None:
        fcf_raw = ocf_raw - capex_raw
        fcf_label = f"${fcf_raw / 1e9:.2f}B"
        out.append(_fmt_row("Free Cash Flow", fcf_label, fcf_raw, metrics.get("period_end_date"), metrics.get("accession_number"), "Computed: OperatingCashFlow - Capex"))
    else:
        out.append("| **Free Cash Flow** | n/a | n/a | n/a | n/a |")

    out.append(_fmt_row("Total Assets", metrics.get("total_assets_label"), metrics.get("total_assets_raw"), metrics.get("total_assets_period") or metrics.get("period_end_date"), metrics.get("total_assets_accession") or metrics.get("accession_number"), metrics.get("total_assets_tag")))
    out.append(_fmt_row("Cash & Equivalents", metrics.get("cash_and_equiv_label"), metrics.get("cash_and_equiv_raw"), metrics.get("cash_and_equiv_period") or metrics.get("period_end_date"), metrics.get("cash_and_equiv_accession") or metrics.get("accession_number"), metrics.get("cash_and_equiv_tag")))
    out.append(_fmt_row("R&D Expense", metrics.get("rd_expense_label"), metrics.get("rd_expense_raw"), metrics.get("rd_expense_period") or metrics.get("period_end_date"), metrics.get("rd_expense_accession") or metrics.get("accession_number"), metrics.get("rd_expense_tag")))

    out.append("")
    out.append(
        "*(Note: All metrics, GAAP tags, accession numbers, and formulas above are rendered directly in code from audited SEC EDGAR XBRL filings. Zero fallback defaults.)*"
    )
    return "\n".join(out)




class XBRLParser:
    """Parses audited financial metrics from SEC EDGAR XBRL company facts."""

    @staticmethod
    def _find_latest_10k_accn(us_gaap: dict[str, Any]) -> str | None:
        """Finds accession number of the latest 10-K filing across all 10-K entries."""
        candidates = []
        for tag_data in us_gaap.values():
            if not isinstance(tag_data, dict) or "units" not in tag_data:
                continue
            for u in tag_data["units"].values():
                for e in u:
                    form = (e.get("form") or "").upper()
                    if "10-K" in form and e.get("accn") and e.get("end"):
                        candidates.append((str(e.get("end")), str(e.get("filed") or ""), str(e["accn"])))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return candidates[0][2]

    @staticmethod
    def _select_metric_entry(
        us_gaap: dict[str, Any],
        tag_candidates: list[str],
        is_instant: bool,
        target_accn: str | None = None,
        target_end_date: str | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Selects the best XBRL entry for a metric matching target accession and duration ~365 days."""
        clean_target_accn = target_accn.replace("-", "") if target_accn else None
        all_considered = []

        for tag in tag_candidates:
            if tag not in us_gaap or "units" not in us_gaap[tag]:
                continue
            units = us_gaap[tag]["units"]
            unit_key = "USD" if "USD" in units else list(units.keys())[0] if units else None
            if not unit_key:
                continue

            for e in units[unit_key]:
                form = (e.get("form") or "").upper()
                if "10-K" not in form:
                    continue
                val = e.get("val")
                if val is None:
                    continue

                start = e.get("start")
                end = e.get("end")
                acc = str(e.get("accn") or "")
                filed = str(e.get("filed") or "")
                clean_acc = acc.replace("-", "")

                days = None
                if start and end:
                    try:
                        s_dt = datetime.strptime(start, "%Y-%m-%d")
                        e_dt = datetime.strptime(end, "%Y-%m-%d")
                        days = (e_dt - s_dt).days
                    except Exception:
                        pass

                entry_rec = {
                    "tag": tag,
                    "val": val,
                    "start": start,
                    "end": end,
                    "days": days,
                    "form": form,
                    "accn": acc,
                    "filed": filed,
                    "fy": e.get("fy"),
                    "fp": e.get("fp"),
                    "from_target_10k": bool(clean_target_accn and clean_acc == clean_target_accn),
                }

                if is_instant:
                    if start is None or days is None or days == 0:
                        all_considered.append(entry_rec)
                else:
                    if days is not None and 330 <= days <= 400:
                        all_considered.append(entry_rec)
                    elif (e.get("fp") or "").upper() == "FY" and start is None:
                        all_considered.append(entry_rec)

        if not all_considered:
            return None, None

        if target_end_date:
            all_considered = [e for e in all_considered if e.get("end") == target_end_date]
            if not all_considered:
                return None, None

        target_entries = [e for e in all_considered if e["from_target_10k"]] if clean_target_accn else []
        pool = target_entries if target_entries else all_considered

        pool_sorted = sorted(pool, key=lambda x: (x.get("end") or "", x.get("filed") or ""), reverse=True)
        chosen = pool_sorted[0]
        return chosen["tag"], chosen

    def parse_metrics(
        self, ticker: str, facts_json: dict[str, Any], target_accn: str | None = None
    ) -> dict[str, Any]:
        """Extracts audited 10-K revenue, gross margin, YoY growth, periods, and accession numbers.

        Extracts both current and prior-year values by period end date and duration (~12 months).
        """
        clean_ticker = ticker.upper()
        facts = facts_json.get("facts", {})
        us_gaap = facts.get("us-gaap", {})
        entity_name = facts_json.get("entityName") or facts_json.get("cik")

        # Determine target 10-K accession if not passed
        if not target_accn:
            target_accn = self._find_latest_10k_accn(us_gaap)

        # 1. Revenue
        rev_tag_used, cur_rev_entry = self._select_metric_entry(
            us_gaap, REVENUE_TAGS, is_instant=False, target_accn=target_accn
        )
        if not cur_rev_entry:
            raise ValueError(f"No annual 10-K revenue facts found in XBRL data for {clean_ticker}")

        cur_end = cur_rev_entry["end"]
        revenue_val = float(cur_rev_entry["val"])
        fy = int(cur_rev_entry.get("fy") or cur_end[:4])
        period_end = cur_end
        accn = str(cur_rev_entry.get("accn") or target_accn or "")

        # Find prior year end date from target 10-K annual entries
        rev_all_target = []
        rev_all_annual = []
        if rev_tag_used and rev_tag_used in us_gaap and "units" in us_gaap[rev_tag_used]:
            u_dict = us_gaap[rev_tag_used]["units"]
            u_list = u_dict.get("USD", [])
            clean_tgt = target_accn.replace("-", "") if target_accn else ""
            for e in u_list:
                form = (e.get("form") or "").upper()
                if "10-K" not in form:
                    continue
                start, end = e.get("start"), e.get("end")
                if not end:
                    continue
                days = None
                if start:
                    try:
                        days = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days
                    except Exception:
                        pass
                is_annual = (days is not None and 330 <= days <= 400) or ((e.get("fp") or "").upper() == "FY" and start is None)
                if is_annual:
                    rev_all_annual.append(end)
                    if str(e.get("accn") or "").replace("-", "") == clean_tgt:
                        rev_all_target.append(end)
        target_annual_ends = sorted(set(rev_all_target), reverse=True)
        prior_end = target_annual_ends[1] if len(target_annual_ends) > 1 else None
        if not prior_end:
            earlier_ends = sorted([ed for ed in set(rev_all_annual) if ed < cur_end], reverse=True)
            prior_end = earlier_ends[0] if earlier_ends else None

        # Prior Revenue & YoY Growth
        growth_yoy = None
        growth_period = "period not stated"
        prior_rev_val = None
        prior_accn = None
        prior_fy = None

        if prior_end:
            _, prev_rev_entry = self._select_metric_entry(
                us_gaap, REVENUE_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )
            if prev_rev_entry:
                prior_rev_val = float(prev_rev_entry["val"])
                prior_accn = str(prev_rev_entry.get("accn") or accn)
                prior_fy = int(prev_rev_entry.get("fy") or prior_end[:4])
                growth_yoy = round(((revenue_val - prior_rev_val) / prior_rev_val) * 100.0, 1)
                growth_period = f"FY ended {period_end} vs FY ended {prior_end}"

        # 2. Gross Profit & Cost of Revenue
        gp_tag_used, cur_gp_entry = self._select_metric_entry(
            us_gaap, GROSS_PROFIT_TAGS, is_instant=False, target_accn=target_accn, target_end_date=cur_end
        )
        cost_tag_used, cur_cost_entry = self._select_metric_entry(
            us_gaap, COST_OF_REVENUE_TAGS, is_instant=False, target_accn=target_accn, target_end_date=cur_end
        )

        cur_gp_val = float(cur_gp_entry["val"]) if cur_gp_entry else None
        cur_cost_val = float(cur_cost_entry["val"]) if cur_cost_entry else None
        margin_tag_used = gp_tag_used

        if cur_gp_val is None and cur_cost_val is not None:
            cur_gp_val = revenue_val - cur_cost_val
            margin_tag_used = f"Computed: ({rev_tag_used} - {cost_tag_used})"

        gross_margin = round((cur_gp_val / revenue_val) * 100.0, 1) if cur_gp_val is not None else None

        # Prior Gross Profit & Cost of Revenue
        prior_gp_val = None
        prior_cost_val = None
        prior_gross_margin = None

        if prior_end:
            _, prev_gp_entry = self._select_metric_entry(
                us_gaap, GROSS_PROFIT_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )
            _, prev_cost_entry = self._select_metric_entry(
                us_gaap, COST_OF_REVENUE_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )
            if prev_gp_entry:
                prior_gp_val = float(prev_gp_entry["val"])
            if prev_cost_entry:
                prior_cost_val = float(prev_cost_entry["val"])
            if prior_gp_val is None and prior_cost_val is not None and prior_rev_val is not None:
                prior_gp_val = prior_rev_val - prior_cost_val
            if prior_gp_val is not None and prior_rev_val:
                prior_gross_margin = round((prior_gp_val / prior_rev_val) * 100.0, 1)

        period_display = f"FY {fy} (ended {period_end})"
        rev_in_billions = round(revenue_val / 1e9, 2)
        gp_in_billions = round(cur_gp_val / 1e9, 2) if cur_gp_val is not None else None
        cost_in_billions = round(cur_cost_val / 1e9, 2) if cur_cost_val is not None else None

        prior_rev_in_billions = round(prior_rev_val / 1e9, 2) if prior_rev_val is not None else None
        prior_gp_in_billions = round(prior_gp_val / 1e9, 2) if prior_gp_val is not None else None
        prior_cost_in_billions = round(prior_cost_val / 1e9, 2) if prior_cost_val is not None else None

        # 3. Core Statement Metrics
        opinc_tag, cur_opinc_entry = self._select_metric_entry(
            us_gaap, OPERATING_INCOME_TAGS, is_instant=False, target_accn=target_accn, target_end_date=cur_end
        )
        ni_tag, cur_ni_entry = self._select_metric_entry(
            us_gaap, NET_INCOME_TAGS, is_instant=False, target_accn=target_accn, target_end_date=cur_end
        )
        rd_tag, cur_rd_entry = self._select_metric_entry(
            us_gaap, RD_EXPENSE_TAGS, is_instant=False, target_accn=target_accn, target_end_date=cur_end
        )
        cash_tag, cur_cash_entry = self._select_metric_entry(
            us_gaap, CASH_AND_EQUIV_TAGS, is_instant=True, target_accn=target_accn, target_end_date=cur_end
        )
        capex_tag, cur_capex_entry = self._select_metric_entry(
            us_gaap, CAPEX_TAGS, is_instant=False, target_accn=target_accn, target_end_date=cur_end
        )
        assets_tag, cur_assets_entry = self._select_metric_entry(
            us_gaap, ASSETS_TAGS, is_instant=True, target_accn=target_accn, target_end_date=cur_end
        )
        ocf_tag, cur_ocf_entry = self._select_metric_entry(
            us_gaap, OPERATING_CASH_FLOW_TAGS, is_instant=False, target_accn=target_accn, target_end_date=cur_end
        )

        cur_opinc_val = float(cur_opinc_entry["val"]) if cur_opinc_entry else None
        cur_opinc_accn = str(cur_opinc_entry.get("accn") or accn) if cur_opinc_entry else None
        cur_ni_val = float(cur_ni_entry["val"]) if cur_ni_entry else None
        cur_ni_accn = str(cur_ni_entry.get("accn") or accn) if cur_ni_entry else None
        cur_rd_val = float(cur_rd_entry["val"]) if cur_rd_entry else None
        cur_rd_accn = str(cur_rd_entry.get("accn") or accn) if cur_rd_entry else None
        cur_cash_val = float(cur_cash_entry["val"]) if cur_cash_entry else None
        cur_cash_accn = str(cur_cash_entry.get("accn") or accn) if cur_cash_entry else None
        cur_capex_val = float(cur_capex_entry["val"]) if cur_capex_entry else None
        cur_capex_accn = str(cur_capex_entry.get("accn") or accn) if cur_capex_entry else None
        cur_assets_val = float(cur_assets_entry["val"]) if cur_assets_entry else None
        cur_assets_accn = str(cur_assets_entry.get("accn") or accn) if cur_assets_entry else None
        cur_ocf_val = float(cur_ocf_entry["val"]) if cur_ocf_entry else None
        cur_ocf_accn = str(cur_ocf_entry.get("accn") or accn) if cur_ocf_entry else None

        # Prior period core metrics
        prior_opinc_val = prior_opinc_accn = None
        prior_ni_val = prior_ni_accn = None
        prior_rd_val = prior_rd_accn = None
        prior_cash_val = prior_cash_accn = None
        prior_capex_val = prior_capex_accn = None
        prior_assets_val = prior_assets_accn = None
        prior_ocf_val = prior_ocf_accn = None

        if prior_end:
            _, prev_opinc_e = self._select_metric_entry(
                us_gaap, OPERATING_INCOME_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )
            _, prev_ni_e = self._select_metric_entry(
                us_gaap, NET_INCOME_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )
            _, prev_rd_e = self._select_metric_entry(
                us_gaap, RD_EXPENSE_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )
            _, prev_cash_e = self._select_metric_entry(
                us_gaap, CASH_AND_EQUIV_TAGS, is_instant=True, target_accn=target_accn, target_end_date=prior_end
            )
            _, prev_capex_e = self._select_metric_entry(
                us_gaap, CAPEX_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )
            _, prev_assets_e = self._select_metric_entry(
                us_gaap, ASSETS_TAGS, is_instant=True, target_accn=target_accn, target_end_date=prior_end
            )
            _, prev_ocf_e = self._select_metric_entry(
                us_gaap, OPERATING_CASH_FLOW_TAGS, is_instant=False, target_accn=target_accn, target_end_date=prior_end
            )

            if prev_opinc_e:
                prior_opinc_val = float(prev_opinc_e["val"])
                prior_opinc_accn = str(prev_opinc_e.get("accn") or accn)
            if prev_ni_e:
                prior_ni_val = float(prev_ni_e["val"])
                prior_ni_accn = str(prev_ni_e.get("accn") or accn)
            if prev_rd_e:
                prior_rd_val = float(prev_rd_e["val"])
                prior_rd_accn = str(prev_rd_e.get("accn") or accn)
            if prev_cash_e:
                prior_cash_val = float(prev_cash_e["val"])
                prior_cash_accn = str(prev_cash_e.get("accn") or accn)
            if prev_capex_e:
                prior_capex_val = float(prev_capex_e["val"])
                prior_capex_accn = str(prev_capex_e.get("accn") or accn)
            if prev_assets_e:
                prior_assets_val = float(prev_assets_e["val"])
                prior_assets_accn = str(prev_assets_e.get("accn") or accn)
            if prev_ocf_e:
                prior_ocf_val = float(prev_ocf_e["val"])
                prior_ocf_accn = str(prev_ocf_e.get("accn") or accn)

        # Derived Financial Metrics & Ratios (Code-computed with exact formulas)
        prior_opinc_margin = round((prior_opinc_val / prior_rev_val) * 100.0, 1) if (prior_opinc_val is not None and prior_rev_val) else None
        cur_opinc_margin = round((cur_opinc_val / revenue_val) * 100.0, 1) if cur_opinc_val is not None else None
        opinc_margin_change_pp = round(cur_opinc_margin - prior_opinc_margin, 1) if (cur_opinc_margin is not None and prior_opinc_margin is not None) else None

        prior_net_margin = round((prior_ni_val / prior_rev_val) * 100.0, 1) if (prior_ni_val is not None and prior_rev_val) else None
        cur_net_margin = round((cur_ni_val / revenue_val) * 100.0, 1) if cur_ni_val is not None else None
        net_margin_change_pp = round(cur_net_margin - prior_net_margin, 1) if (cur_net_margin is not None and prior_net_margin is not None) else None

        gross_margin_change_pp = round(gross_margin - prior_gross_margin, 1) if (gross_margin is not None and prior_gross_margin is not None) else None

        opinc_growth_yoy = round(((cur_opinc_val - prior_opinc_val) / prior_opinc_val) * 100.0, 1) if (cur_opinc_val is not None and prior_opinc_val) else None
        net_income_growth_yoy = round(((cur_ni_val - prior_ni_val) / prior_ni_val) * 100.0, 1) if (cur_ni_val is not None and prior_ni_val) else None
        rd_growth_yoy = round(((cur_rd_val - prior_rd_val) / prior_rd_val) * 100.0, 1) if (cur_rd_val is not None and prior_rd_val) else None
        capex_growth_yoy = round(((cur_capex_val - prior_capex_val) / prior_capex_val) * 100.0, 1) if (cur_capex_val is not None and prior_capex_val) else None

        rd_pct_rev = round((cur_rd_val / revenue_val) * 100.0, 1) if (cur_rd_val is not None and revenue_val) else None
        capex_pct_rev = round((cur_capex_val / revenue_val) * 100.0, 1) if (cur_capex_val is not None and revenue_val) else None
        cost_pct_rev = round((cur_cost_val / revenue_val) * 100.0, 1) if (cur_cost_val is not None and revenue_val) else None

        gm_change_formula = f"{gross_margin}% - {prior_gross_margin}% = {gross_margin_change_pp:+} pp" if gross_margin_change_pp is not None else None
        opinc_margin_formula = f"${round(cur_opinc_val / 1e9, 2)}B / ${rev_in_billions}B = {cur_opinc_margin}%" if cur_opinc_margin is not None else None
        opinc_margin_change_formula = f"{cur_opinc_margin}% - {prior_opinc_margin}% = {opinc_margin_change_pp:+} pp" if opinc_margin_change_pp is not None else None
        net_margin_formula = f"${round(cur_ni_val / 1e9, 2)}B / ${rev_in_billions}B = {cur_net_margin}%" if cur_net_margin is not None else None
        net_margin_change_formula = f"{cur_net_margin}% - {prior_net_margin}% = {net_margin_change_pp:+} pp" if net_margin_change_pp is not None else None
        opinc_growth_formula = f"(${round(cur_opinc_val / 1e9, 2)}B - ${round(prior_opinc_val / 1e9, 2)}B) / ${round(prior_opinc_val / 1e9, 2)}B = {opinc_growth_yoy:+}%" if opinc_growth_yoy is not None else None
        ni_growth_formula = f"(${round(cur_ni_val / 1e9, 2)}B - ${round(prior_ni_val / 1e9, 2)}B) / ${round(prior_ni_val / 1e9, 2)}B = {net_income_growth_yoy:+}%" if net_income_growth_yoy is not None else None
        rd_growth_formula = f"(${round(cur_rd_val / 1e9, 2)}B - ${round(prior_rd_val / 1e9, 2)}B) / ${round(prior_rd_val / 1e9, 2)}B = {rd_growth_yoy:+}%" if rd_growth_yoy is not None else None
        capex_growth_formula = f"(${round(cur_capex_val / 1e9, 2)}B - ${round(prior_capex_val / 1e9, 2)}B) / ${round(prior_capex_val / 1e9, 2)}B = {capex_growth_yoy:+}%" if capex_growth_yoy is not None else None
        rd_pct_formula = f"${round(cur_rd_val / 1e9, 2)}B / ${rev_in_billions}B = {rd_pct_rev}%" if rd_pct_rev is not None else None
        capex_pct_formula = f"${round(cur_capex_val / 1e9, 2)}B / ${rev_in_billions}B = {capex_pct_rev}%" if capex_pct_rev is not None else None
        cost_pct_formula = f"${round(cur_cost_val / 1e9, 2)}B / ${rev_in_billions}B = {cost_pct_rev}%" if cost_pct_rev is not None else None

        return {
            "ticker": clean_ticker,
            "company_name": entity_name,
            "source": "SEC filing",
            "source_label": "SEC filing",
            "source_badge": "SEC filing (XBRL)",
            "fiscal_year": fy,
            "period_end_date": period_end,
            "accession_number": accn,
            "revenue": rev_in_billions,
            "revenue_raw": revenue_val,
            "revenue_label": f"${rev_in_billions}B",
            "revenue_source": "SEC filing",
            "revenue_period": period_display,
            "revenue_accession": accn,
            "revenue_tag": rev_tag_used,
            "gross_profit": gp_in_billions,
            "gross_profit_raw": cur_gp_val,
            "gross_profit_label": f"${gp_in_billions}B" if gp_in_billions is not None else None,
            "gross_profit_tag": gp_tag_used,
            "cost_of_revenue": cost_in_billions,
            "cost_of_revenue_raw": cur_cost_val,
            "cost_label": f"${cost_in_billions}B" if cost_in_billions is not None else None,
            "cost_tag": cost_tag_used,
            "gross_margin": gross_margin,
            "margin_label": f"{gross_margin}%" if gross_margin is not None else "N/A",
            "margin_source": "SEC filing",
            "margin_period": period_display,
            "margin_accession": accn,
            "margin_tag": margin_tag_used,
            "growth_yoy": growth_yoy,
            "growth_label": f"{growth_yoy:+}%" if growth_yoy is not None else "N/A",
            "growth_source": "SEC filing",
            "growth_period": growth_period,
            "growth_accession": accn,
            "operating_income": round(cur_opinc_val / 1e9, 2) if cur_opinc_val is not None else None,
            "operating_income_raw": cur_opinc_val,
            "operating_income_label": f"${round(cur_opinc_val / 1e9, 2)}B" if cur_opinc_val is not None else None,
            "operating_income_tag": opinc_tag,
            "operating_income_accession": cur_opinc_accn,
            "operating_income_period": period_end,
            "net_income": round(cur_ni_val / 1e9, 2) if cur_ni_val is not None else None,
            "net_income_raw": cur_ni_val,
            "net_income_label": f"${round(cur_ni_val / 1e9, 2)}B" if cur_ni_val is not None else None,
            "net_income_tag": ni_tag,
            "net_income_accession": cur_ni_accn,
            "net_income_period": period_end,
            "total_assets": round(cur_assets_val / 1e9, 2) if cur_assets_val is not None else None,
            "total_assets_raw": cur_assets_val,
            "total_assets_label": f"${round(cur_assets_val / 1e9, 2)}B" if cur_assets_val is not None else None,
            "total_assets_tag": assets_tag,
            "total_assets_accession": cur_assets_accn,
            "total_assets_period": period_end,
            "operating_cash_flow": round(cur_ocf_val / 1e9, 2) if cur_ocf_val is not None else None,
            "operating_cash_flow_raw": cur_ocf_val,
            "operating_cash_flow_label": f"${round(cur_ocf_val / 1e9, 2)}B" if cur_ocf_val is not None else None,
            "operating_cash_flow_tag": ocf_tag,
            "operating_cash_flow_accession": cur_ocf_accn,
            "operating_cash_flow_period": period_end,
            "rd_expense": round(cur_rd_val / 1e9, 2) if cur_rd_val is not None else None,
            "rd_expense_raw": cur_rd_val,
            "rd_expense_label": f"${round(cur_rd_val / 1e9, 2)}B" if cur_rd_val is not None else None,
            "rd_expense_tag": rd_tag,
            "rd_expense_accession": cur_rd_accn,
            "rd_expense_period": period_end,
            "cash_and_equiv": round(cur_cash_val / 1e9, 2) if cur_cash_val is not None else None,
            "cash_and_equiv_raw": cur_cash_val,
            "cash_and_equiv_label": f"${round(cur_cash_val / 1e9, 2)}B" if cur_cash_val is not None else None,
            "cash_and_equiv_tag": cash_tag,
            "cash_and_equiv_accession": cur_cash_accn,
            "cash_and_equiv_period": period_end,
            "capex": round(cur_capex_val / 1e9, 2) if cur_capex_val is not None else None,
            "capex_raw": cur_capex_val,
            "capex_label": f"${round(cur_capex_val / 1e9, 2)}B" if cur_capex_val is not None else None,
            "capex_tag": capex_tag,
            "capex_accession": cur_capex_accn,
            "capex_period": period_end,
            "prior_fiscal_year": prior_fy,
            "prior_period_end_date": prior_end,
            "prior_accession_number": prior_accn,
            "prior_revenue": prior_rev_in_billions,
            "prior_revenue_raw": prior_rev_val,
            "prior_revenue_label": f"${prior_rev_in_billions}B" if prior_rev_in_billions is not None else None,
            "prior_gross_profit": prior_gp_in_billions,
            "prior_gross_profit_raw": prior_gp_val,
            "prior_gross_profit_label": f"${prior_gp_in_billions}B" if prior_gp_in_billions is not None else None,
            "prior_cost_of_revenue": prior_cost_in_billions,
            "prior_cost_raw": prior_cost_val,
            "prior_cost_label": f"${prior_cost_in_billions}B" if prior_cost_in_billions is not None else None,
            "prior_gross_margin": prior_gross_margin,
            "prior_margin_label": f"{prior_gross_margin}%" if prior_gross_margin is not None else None,
            "prior_operating_income": round(prior_opinc_val / 1e9, 2) if prior_opinc_val is not None else None,
            "prior_operating_income_raw": prior_opinc_val,
            "prior_operating_income_label": f"${round(prior_opinc_val / 1e9, 2)}B" if prior_opinc_val is not None else None,
            "prior_net_income": round(prior_ni_val / 1e9, 2) if prior_ni_val is not None else None,
            "prior_net_income_raw": prior_ni_val,
            "prior_net_income_label": f"${round(prior_ni_val / 1e9, 2)}B" if prior_ni_val is not None else None,
            "prior_total_assets": round(prior_assets_val / 1e9, 2) if prior_assets_val is not None else None,
            "prior_total_assets_raw": prior_assets_val,
            "prior_total_assets_label": f"${round(prior_assets_val / 1e9, 2)}B" if prior_assets_val is not None else None,
            "prior_operating_cash_flow": round(prior_ocf_val / 1e9, 2) if prior_ocf_val is not None else None,
            "prior_operating_cash_flow_raw": prior_ocf_val,
            "prior_operating_cash_flow_label": f"${round(prior_ocf_val / 1e9, 2)}B" if prior_ocf_val is not None else None,
            "prior_rd_expense": round(prior_rd_val / 1e9, 2) if prior_rd_val is not None else None,
            "prior_rd_expense_raw": prior_rd_val,
            "prior_rd_expense_label": f"${round(prior_rd_val / 1e9, 2)}B" if prior_rd_val is not None else None,
            "prior_cash_and_equiv": round(prior_cash_val / 1e9, 2) if prior_cash_val is not None else None,
            "prior_cash_and_equiv_raw": prior_cash_val,
            "prior_cash_and_equiv_label": f"${round(prior_cash_val / 1e9, 2)}B" if prior_cash_val is not None else None,
            "prior_capex": round(prior_capex_val / 1e9, 2) if prior_capex_val is not None else None,
            "prior_capex_raw": prior_capex_val,
            "prior_capex_label": f"${round(prior_capex_val / 1e9, 2)}B" if prior_capex_val is not None else None,
            "primary_driver": None,
            "driver_source": None,
            "driver_period": None,
            "driver_accession": None,
            "cloud_ai_revenue": None,
            "gross_margin_change": gross_margin_change_pp,
            "gross_margin_change_label": f"{gross_margin_change_pp:+} pp" if gross_margin_change_pp is not None else None,
            "gross_margin_change_formula": gm_change_formula,
            "operating_margin": cur_opinc_margin,
            "operating_margin_label": f"{cur_opinc_margin}%" if cur_opinc_margin is not None else None,
            "operating_margin_formula": opinc_margin_formula,
            "prior_operating_margin": prior_opinc_margin,
            "operating_margin_change": opinc_margin_change_pp,
            "operating_margin_change_label": f"{opinc_margin_change_pp:+} pp" if opinc_margin_change_pp is not None else None,
            "operating_margin_change_formula": opinc_margin_change_formula,
            "net_margin": cur_net_margin,
            "net_margin_label": f"{cur_net_margin}%" if cur_net_margin is not None else None,
            "net_margin_formula": net_margin_formula,
            "prior_net_margin": prior_net_margin,
            "net_margin_change": net_margin_change_pp,
            "net_margin_change_label": f"{net_margin_change_pp:+} pp" if net_margin_change_pp is not None else None,
            "net_margin_change_formula": net_margin_change_formula,
            "opinc_growth_yoy": opinc_growth_yoy,
            "opinc_growth_label": f"{opinc_growth_yoy:+}%" if opinc_growth_yoy is not None else None,
            "opinc_growth_formula": opinc_growth_formula,
            "net_income_growth_yoy": net_income_growth_yoy,
            "net_income_growth_label": f"{net_income_growth_yoy:+}%" if net_income_growth_yoy is not None else None,
            "net_income_growth_formula": ni_growth_formula,
            "rd_growth_yoy": rd_growth_yoy,
            "rd_growth_label": f"{rd_growth_yoy:+}%" if rd_growth_yoy is not None else None,
            "rd_growth_formula": rd_growth_formula,
            "capex_growth_yoy": capex_growth_yoy,
            "capex_growth_label": f"{capex_growth_yoy:+}%" if capex_growth_yoy is not None else None,
            "capex_growth_formula": capex_growth_formula,
            "rd_percent_of_revenue": rd_pct_rev,
            "rd_percent_of_revenue_label": f"{rd_pct_rev}%" if rd_pct_rev is not None else None,
            "rd_percent_of_revenue_formula": rd_pct_formula,
            "capex_percent_of_revenue": capex_pct_rev,
            "capex_percent_of_revenue_label": f"{capex_pct_rev}%" if capex_pct_rev is not None else None,
            "capex_percent_of_revenue_formula": capex_pct_formula,
            "cost_percent_of_revenue": cost_pct_rev,
            "cost_percent_of_revenue_label": f"{cost_pct_rev}%" if cost_pct_rev is not None else None,
            "cost_percent_of_revenue_formula": cost_pct_formula,
            "sentiment": (
                f"FY {fy} (ended {period_end}): Revenue ${rev_in_billions}B"
                + (f", YoY {growth_yoy:+}%" if growth_yoy is not None else "")
                + (f", Gross Margin {gross_margin}%" if gross_margin is not None else "")
            ),
            "reason": None,
        }


MONTHS_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}


def parse_iso_date(text: str, default_month_day: str = "") -> str:
    """Parses date string into YYYY-MM-DD format."""
    # Pattern 1: Month Day, Year (e.g. 'Jan 25, 2026' or 'September 26, 2026')
    m1 = re.search(
        r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*(\d{1,2}),?\s*(202\d)\b",
        text,
        re.I,
    )
    if m1:
        mon = MONTHS_MAP[m1.group(1).lower()]
        day = int(m1.group(2))
        yr = m1.group(3)
        return f"{yr}-{mon}-{day:02d}"

    # Pattern 2: YYYY-MM-DD
    m2 = re.search(r"\b(202\d)-(\d{2})-(\d{2})\b", text)
    if m2:
        return m2.group(0)

    # Pattern 3: Year with default_month_day (e.g. 'June 30' or 'December 31')
    m3 = re.search(r"\b(202\d)\b", text)
    if m3 and default_month_day:
        yr = m3.group(1)
        m_md = re.search(
            r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*(\d{1,2})\b",
            default_month_day,
            re.I,
        )
        if m_md:
            mon = MONTHS_MAP[m_md.group(1).lower()]
            day = int(m_md.group(2))
            return f"{yr}-{mon}-{day:02d}"

    return ""


def convert_table_to_structured_text(table_tag: Any, surrounding_text: str = "") -> str:
    """Converts an HTML table into structured text rows.

    Handles:
    - '$' in separate cells
    - Negatives in parentheses: '(x)' -> '-x'
    - Em/en dashes: '—'
    - Colspan and multi-row headers without duplicating line items
    - Footnote markers
    - Units in caption or header
    - Layout table neutralization/dropping (signatures, TOC, index)
    - True ISO period end dates alongside fiscal year labels: 'FY2026 (2026-01-25)'
    - Chronological ordering: ensures column 1 is always the latest fiscal period
    """
    all_text = table_tag.get_text(separator=" ")
    clean_all = re.sub(r"\s+", " ", all_text).strip()

    # Drop signature blocks, cover page metadata, and TOC layout tables
    if any(sig in clean_all for sig in ["/s/", "By:", "Title:", "Indicate by check mark"]):
        num_matches = re.findall(r"\b\d{1,3}(?:,\d{3})+\b", clean_all)
        if len(num_matches) < 2:
            return ""

    if any(
        toc in clean_all
        for toc in [
            "Index to Consolidated Financial Statements",
            "INDEX TO CONSOLIDATED FINANCIAL STATEMENTS",
            "Index to Financial Statements",
        ]
    ):
        return ""

    unit_match = re.search(
        r"\((?:in\s+millions|in\s+thousands|in\s+billions|\$\s*in\s+millions|usd\s+millions|in\s+millions,\s*except[^\)]*)\)",
        clean_all[:400] + " " + surrounding_text,
        re.I,
    )
    units_str = unit_match.group(0).strip() if unit_match else ""
    if not units_str and "in millions" in clean_all[:200].lower():
        units_str = "(in millions)"

    trs = table_tag.find_all("tr")
    if not trs:
        return ""

    grid: list[list[str]] = []
    for tr in trs:
        row_cells: list[str] = []
        for cell in tr.find_all(["td", "th"]):
            colspan = int(cell.get("colspan", 1))
            c_text = cell.get_text(separator=" ")
            c_text = re.sub(r"\s+", " ", c_text).strip()
            row_cells.append(c_text)
            for _ in range(colspan - 1):
                row_cells.append("")
        grid.append(row_cells)

    if not grid:
        return ""

    cleaned_rows: list[list[str]] = []
    for r in grid:
        merged: list[str] = []
        i = 0
        while i < len(r):
            val = r[i]
            if val == "$" and i + 1 < len(r) and re.search(r"\d", r[i + 1]):
                val = "$" + r[i + 1]
                i += 1
            elif val == "(" and i + 1 < len(r) and re.search(r"\d", r[i + 1]):
                if i + 2 < len(r) and r[i + 2] == ")":
                    val = f"-{r[i + 1]}"
                    i += 2
                else:
                    val = f"-{r[i + 1]}"
                    i += 1
            paren_m = re.match(r"^\(\s*[\$]?\s*([0-9,.]+)\s*\)$", val)
            if paren_m:
                val = f"-{paren_m.group(1)}"
            cur_paren = re.match(r"^\(?\s*\$\s*\(?\s*([0-9,.]+)\s*\)?\)?$", val)
            if cur_paren and ("(" in val or ")" in val):
                val = f"-${cur_paren.group(1)}"

            # merge following '%'
            if i + 1 < len(r) and r[i + 1].strip() == "%":
                val = f"{val}%"
                i += 1
            elif val == "%" and merged and re.search(r"\d", merged[-1]):
                merged[-1] = f"{merged[-1]}%"
                i += 1
                continue

            val = re.sub(r"\s*\([a-z0-9]\)$", "", val, flags=re.I).strip()
            if val in ["—", "–", "-"]:
                val = "—"
            if val:
                merged.append(val)
            i += 1
        if merged:
            cleaned_rows.append(merged)

    if not cleaned_rows:
        return ""

    # Check for spanning month/day in top 5 rows (e.g. 'Year Ended June 30,' or 'Year Ended December 31,')
    top_header_text = " ".join([" ".join(r) for r in cleaned_rows[:5]])
    default_md = ""
    md_match = re.search(
        r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*(\d{1,2})\b",
        top_header_text,
        re.I,
    )
    if md_match:
        default_md = f"{md_match.group(1)} {md_match.group(2)}"

    col_headers: list[str] = []
    col_years: list[int] = []
    data_start = 0
    for r_idx, r in enumerate(cleaned_rows[:6]):
        years = [re.search(r"\b(202\d)\b", c) for c in r]
        has_years = any(years)
        has_values = any(re.search(r"^\$?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?$", c) for c in r)
        if has_years or (not has_values and r_idx == 0):
            extracted: list[str] = []
            extracted_yrs: list[int] = []
            for c in r:
                ym = re.search(r"\b(202\d)\b", c)
                if ym:
                    yr = ym.group(1)
                    iso = parse_iso_date(c, default_month_day=default_md)
                    label = f"FY{yr} ({iso})" if iso else f"FY{yr}"
                    extracted.append(label)
                    extracted_yrs.append(int(yr))
                elif re.search(r"[a-zA-Z]", c) and len(c) < 30:
                    extracted.append(c)
            if extracted:
                col_headers = extracted
                col_years = extracted_yrs
            data_start = r_idx + 1
        else:
            break

    # Reversal rule: ONLY reverse if pure years table (all column headers are years)
    reverse_cols = False
    if (
        len(col_years) >= 2
        and len(col_years) == len(col_headers)
        and col_years == sorted(col_years)
        and col_years[0] < col_years[-1]
    ):
        reverse_cols = True
        col_headers.reverse()

    lines: list[str] = []
    for r in cleaned_rows[data_start:]:
        label = ""
        vals: list[str] = []
        for c in r:
            is_val = bool(re.search(r"^\$?-?\d", c) or c == "—" or "%" in c or "pts" in c)
            if not label and not is_val:
                label = c
            else:
                if is_val:
                    vals.append(c)
                elif not label:
                    label = c
                else:
                    label += f" {c}"
        if not label or not vals:
            continue

        if reverse_cols and len(vals) == len(col_headers):
            vals.reverse()

        active_headers = col_headers
        if len(active_headers) == len(vals) + 1:
            active_headers = active_headers[1:]
        elif len(active_headers) > len(vals) and active_headers and active_headers[0].lower() in [
            "line item", "metric", "description", "statement", "consolidated statement", "company / index", "impact"
        ]:
            active_headers = active_headers[1:]

        # Validate alignment: period label must never be attached to change or percent cell
        is_aligned = (len(vals) == len(active_headers))
        parts = [label]

        if not is_aligned:
            parts.append("[unaligned]")
            for v in vals:
                parts.append(v)
        else:
            has_error = False
            temp_parts = []
            for h, v in zip(active_headers, vals):
                is_period_hdr = "FY20" in h
                if is_period_hdr and (v == "%" or v == "Change" or v.lower() == "pts"):
                    has_error = True
                    break
                temp_parts.append(f"{h}: {v}")
            if has_error:
                parts.append("[unaligned]")
                for v in vals:
                    parts.append(v)
            else:
                parts.extend(temp_parts)

        line = " | ".join(parts)
        if units_str and units_str not in line:
            line += f" {units_str}"
        lines.append(line)

    return "\n".join(lines)


class Form10KParser:
    """Extracts Items 1, 1A, 7, 8 from Form 10-K primary document HTML/text."""

    @staticmethod
    def html_to_clean_text(html_content: str) -> str:
        """Strips scripts/styles, converts HTML tables to structured line-item text, and normalizes whitespace."""
        soup = BeautifulSoup(html_content, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        for tbl in soup.find_all("table"):
            prev = tbl.find_previous(["p", "div", "h1", "h2", "h3", "h4", "span"])
            prev_text = prev.get_text() if prev else ""
            converted = convert_table_to_structured_text(tbl, prev_text)
            if converted:
                tbl.replace_with(soup.new_string(f"\n[TABLE_START]\n{converted}\n[TABLE_END]\n"))
            else:
                tbl.decompose()

        text = soup.get_text(separator="\n")
        text = text.replace("\xa0", " ")
        lines = [line.strip() for line in text.splitlines()]
        clean_lines = [line for line in lines if line]
        return "\n".join(clean_lines)

    @classmethod
    def extract_items(cls, text: str) -> dict[str, str]:
        """Extracts Item 1, Item 1A, Item 7, Item 8 text blocks.

        Handles drop caps, broken words, table of contents avoidance,
        and redirects Item 8 to Item 15 when Item 8 is a short cross-reference.
        """
        results = {
            "Item 1": "",
            "Item 1A": "",
            "Item 7": "",
            "Item 8": "",
        }

        # Item 1: Business
        m1 = list(
            re.finditer(
                r"(?:^|\n)\s*(?:ITEM\s+1\.?|Item\s+1\.?)\s*(?:[-:–—]\s*)?B\s*USINESS",
                text,
                re.IGNORECASE,
            )
        )
        # Item 1A: Risk Factors
        m1a = list(
            re.finditer(
                r"(?:^|\n)\s*(?:ITEM\s+1A\.?|Item\s+1A\.?)\s*(?:[-:–—]\s*)?R\s*I\s*S\s*[-–—]?\s*K\s*FACTORS",
                text,
                re.IGNORECASE,
            )
        )
        # Item 7: Management's Discussion and Analysis
        m7 = list(
            re.finditer(
                r"(?:^|\n)\s*(?:ITEM\s+7\.?|Item\s+7\.?)\s*(?:[-:–—]\s*)?M\s*ANAGEMENT",
                text,
                re.IGNORECASE,
            )
        )
        # Item 8: Financial Statements
        m8 = list(
            re.finditer(
                r"(?:^|\n)\s*(?:ITEM\s+8\.?|Item\s+8\.?)\s*(?:[-:–—]\s*)?F\s*INANCIAL\s+STATE\s*[-–—]?\s*MENTS",
                text,
                re.IGNORECASE,
            )
        )

        # Slicing Item 1
        if m1:
            s1 = m1[-1].start()
            e1 = (
                m1a[-1].start()
                if m1a and m1a[-1].start() > s1
                else s1 + 45000
            )
            results["Item 1"] = text[s1:e1].strip()

        # Slicing Item 1A
        if m1a:
            s1a = m1a[-1].start()
            end_match = re.search(
                r"(?:^|\n)\s*(?:ITEM\s+1B\.?|ITEM\s+2\.?|Item\s+1B\.?|Item\s+2\.?)",
                text[s1a + 100:],
                re.IGNORECASE,
            )
            e1a = s1a + 100 + end_match.start() if end_match else s1a + 80000
            results["Item 1A"] = text[s1a:e1a].strip()

        # Slicing Item 7
        if m7:
            s7 = m7[-1].start()
            end_7 = re.search(
                r"(?:^|\n)\s*(?:ITEM\s+7A\.?|ITEM\s+8\.?|Item\s+7A\.?|Item\s+8\.?)",
                text[s7 + 100:],
                re.IGNORECASE,
            )
            e7 = s7 + 100 + end_7.start() if end_7 else s7 + 60000
            results["Item 7"] = text[s7:e7].strip()

        # Slicing Item 8 (with Item 15 redirection when Item 8 is a short cross-reference)
        if m8:
            s8 = m8[-1].start()
            end_8 = re.search(
                r"(?:^|\n)\s*(?:ITEM\s+9\.?|Item\s+9\.?)",
                text[s8 + 100:],
                re.IGNORECASE,
            )
            e8 = s8 + 100 + end_8.start() if end_8 else s8 + 60000
            item8_text = text[s8:e8].strip()

            item8_words = len(item8_text.split())
            if item8_words < 100 and any(
                k in item8_text.lower()
                for k in ["item 15", "part iv", "set forth", "consolidated financial statements"]
            ):
                m15 = list(re.finditer(
                    r"(?:^|\n)\s*(?:ITEM\s+15\.?|Item\s+15\.?)\s*(?:[-:–—]\s*)?EXHIBITS",
                    text,
                    re.IGNORECASE,
                ))
                if m15:
                    s15 = m15[-1].start()
                    end_15 = re.search(
                        r"(?:^|\n)\s*(?:ITEM\s+16\.?|Item\s+16\.?|SIGNATURES)",
                        text[s15 + 100:],
                        re.IGNORECASE,
                    )
                    e15 = s15 + 100 + end_15.start() if end_15 else len(text)
                    item8_text = (
                        f"{item8_text}\n\n"
                        f"=== FINANCIAL STATEMENTS & NOTES (VIA ITEM 15 REDIRECT) ===\n\n"
                        f"{text[s15:e15].strip()}"
                    )
            results["Item 8"] = item8_text

        return results


class SECIngestionService:
    """Orchestrates compliant SEC EDGAR ingestion, document preparation, and disk caching."""

    def __init__(self, client: SECClient | None = None):
        self.client = client or SECClient()
        self.xbrl_parser = XBRLParser()
        self.form_parser = Form10KParser()

    def find_latest_10k_submission(self, submissions_json: dict[str, Any]) -> dict[str, str]:
        """Finds accession number and primary document name of latest Form 10-K."""
        recent = submissions_json.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])

        for idx, form in enumerate(forms):
            if form == "10-K":
                return {
                    "accessionNumber": accessions[idx],
                    "primaryDocument": primary_docs[idx],
                    "filingDate": filing_dates[idx] if idx < len(filing_dates) else "",
                    "reportDate": report_dates[idx] if idx < len(report_dates) else "",
                }

        raise ValueError("No Form 10-K found in recent submissions.")

    def ingest_ticker(self, ticker: str, cik: str) -> tuple[dict[str, Any], str, dict[str, int]]:
        """Ingests facts and 10-K document for a ticker, returns (metrics, document_text, item_char_counts)."""
        clean_ticker = ticker.upper()
        logger.info(f"Starting SEC EDGAR ingestion for {clean_ticker} (CIK: {cik})")

        # 1. Submissions & Target 10-K Accession
        submissions = self.client.get_submissions(cik)
        submission_10k = self.find_latest_10k_submission(submissions)
        accn = submission_10k["accessionNumber"]
        primary_doc = submission_10k["primaryDocument"]

        # 2. Company Facts (XBRL)
        facts = self.client.get_company_facts(cik)
        metrics = self.xbrl_parser.parse_metrics(clean_ticker, facts, target_accn=accn)

        # 3. Primary 10-K Document
        doc_raw = self.client.get_filing_document(cik, accn, primary_doc)
        doc_text = self.form_parser.html_to_clean_text(doc_raw)
        items = self.form_parser.extract_items(doc_text)

        # Build article text with explicit metadata header
        metadata_header = (
            f"[DOCUMENT_METADATA]\n"
            f"Document Type: SEC filing\n"
            f"Source: SEC EDGAR\n"
            f"Ticker: {clean_ticker}\n"
            f"Company Name: {metrics['company_name']}\n"
            f"CIK: {str(cik).zfill(10)}\n"
            f"Form: 10-K\n"
            f"Fiscal Year: {metrics['fiscal_year']}\n"
            f"Period End Date: {metrics['period_end_date']}\n"
            f"Accession Number: {accn}\n"
            f"Filing Date: {submission_10k.get('filingDate', 'N/A')}\n"
            f"Total Revenue: {metrics['revenue_label']} ({metrics['revenue_period']}) [Accession: {accn}]\n"
            f"Gross Margin: {metrics['margin_label']} ({metrics['margin_period']}) [Accession: {accn}]\n"
            f"YoY Growth: {metrics['growth_label']} ({metrics['growth_period']}) [Accession: {accn}]\n"
            f"[/DOCUMENT_METADATA]\n\n"
        )

        sections = [metadata_header]
        char_counts = {}

        for item_name in ["Item 1", "Item 1A", "Item 7", "Item 8"]:
            content = items.get(item_name, "").strip()
            char_counts[item_name] = len(content)
            if content:
                sections.append(f"=== {item_name.upper()} ===\n{content}\n\n")
            else:
                sections.append(
                    f"=== {item_name.upper()} ===\n"
                    f"[{item_name} not found as separate text section in primary filing document]\n\n"
                )

        full_doc = "".join(sections)
        return metrics, full_doc, char_counts


sec_client = SECClient()
sec_ingestion_service = SECIngestionService(client=sec_client)
