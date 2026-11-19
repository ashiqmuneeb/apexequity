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

    lines.append("=== END VERIFIED FACTS ===")
    return "\n".join(lines)


class XBRLParser:
    """Parses audited financial metrics from SEC EDGAR XBRL company facts."""

    @staticmethod
    def _filter_annual_10k(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Filters entries for Form 10-K full fiscal year disclosures (~12 month duration).

        Groups by period end date and retains the most recently filed entry for restatements.
        """
        by_end: dict[str, dict[str, Any]] = {}
        for e in entries:
            form = (e.get("form") or "").upper()
            if "10-K" not in form:
                continue
            start = e.get("start")
            end = e.get("end")
            val = e.get("val")
            if val is None or not end:
                continue

            is_annual = False
            if start and end:
                try:
                    s_dt = datetime.strptime(start, "%Y-%m-%d")
                    e_dt = datetime.strptime(end, "%Y-%m-%d")
                    days = (e_dt - s_dt).days
                    if 330 <= days <= 400:
                        is_annual = True
                except Exception:
                    pass
            elif (e.get("fp") or "").upper() == "FY":
                is_annual = True

            if is_annual:
                # If end date already present, keep the most recently filed one (for restatements)
                existing = by_end.get(end)
                if existing is None or str(e.get("filed") or "") > str(existing.get("filed") or ""):
                    by_end[end] = e

        return by_end

    def _find_best_annual_facts(
        self, gaap_facts: dict[str, Any], tag_candidates: list[str]
    ) -> tuple[str | None, dict[str, dict[str, Any]]]:
        """Finds candidate tag that contains the most recent 10-K annual facts."""
        best_tag = None
        best_entries: dict[str, dict[str, Any]] = {}
        best_latest_date = ""

        for tag in tag_candidates:
            if tag in gaap_facts and "units" in gaap_facts[tag]:
                units = gaap_facts[tag]["units"]
                if "USD" in units:
                    annual_map = self._filter_annual_10k(units["USD"])
                    if annual_map:
                        latest_date = max(annual_map.keys())
                        if latest_date > best_latest_date:
                            best_latest_date = latest_date
                            best_tag = tag
                            best_entries = annual_map

        return best_tag, best_entries

    def parse_metrics(self, ticker: str, facts_json: dict[str, Any]) -> dict[str, Any]:
        """Extracts audited 10-K revenue, gross margin, YoY growth, periods, and accession numbers.

        Extracts both current and prior-year values by period end date and duration (~12 months).
        """
        clean_ticker = ticker.upper()
        facts = facts_json.get("facts", {})
        us_gaap = facts.get("us-gaap", {})
        entity_name = facts_json.get("entityName") or facts_json.get("cik")

        # 1. Revenue
        rev_tag, annual_rev = self._find_best_annual_facts(us_gaap, REVENUE_TAGS)
        if not annual_rev:
            raise ValueError(f"No annual 10-K revenue facts found in XBRL data for {clean_ticker}")

        sorted_rev_ends = sorted(annual_rev.keys(), reverse=True)
        cur_end = sorted_rev_ends[0]
        prior_end = sorted_rev_ends[1] if len(sorted_rev_ends) > 1 else None

        cur_rev_entry = annual_rev[cur_end]
        revenue_val = float(cur_rev_entry["val"])
        fy = int(cur_rev_entry.get("fy") or cur_end[:4])
        period_end = cur_end
        accn = str(cur_rev_entry.get("accn") or "")
        rev_tag_used = rev_tag

        # Prior Revenue & YoY Growth
        growth_yoy = None
        growth_period = "period not stated"
        prior_rev_val = None
        prior_accn = None
        prior_fy = None

        if prior_end and prior_end in annual_rev:
            prev_rev_entry = annual_rev[prior_end]
            prior_rev_val = float(prev_rev_entry["val"])
            prior_accn = str(prev_rev_entry.get("accn") or accn)
            prior_fy = int(prev_rev_entry.get("fy") or prior_end[:4])
            growth_yoy = round(((revenue_val - prior_rev_val) / prior_rev_val) * 100.0, 1)
            growth_period = f"FY ended {period_end} vs FY ended {prior_end}"

        # 2. Gross Profit & Cost of Revenue
        gp_tag, annual_gp = self._find_best_annual_facts(us_gaap, GROSS_PROFIT_TAGS)
        cost_tag, annual_cost = self._find_best_annual_facts(us_gaap, COST_OF_REVENUE_TAGS)

        # Current period Gross Margin
        cur_gp_val = None
        cur_cost_val = None
        margin_tag_used = None
        cost_tag_used = None

        if annual_gp and cur_end in annual_gp:
            cur_gp_val = float(annual_gp[cur_end]["val"])
            margin_tag_used = gp_tag
        if annual_cost and cur_end in annual_cost:
            cur_cost_val = float(annual_cost[cur_end]["val"])
            cost_tag_used = cost_tag

        if cur_gp_val is None and cur_cost_val is not None:
            cur_gp_val = revenue_val - cur_cost_val
            margin_tag_used = f"Computed: ({rev_tag} - {cost_tag})"

        gross_margin = round((cur_gp_val / revenue_val) * 100.0, 1) if cur_gp_val is not None else None

        # Prior period Gross Margin
        prior_gp_val = None
        prior_cost_val = None
        prior_gross_margin = None

        if prior_end:
            if annual_gp and prior_end in annual_gp:
                prior_gp_val = float(annual_gp[prior_end]["val"])
            if annual_cost and prior_end in annual_cost:
                prior_cost_val = float(annual_cost[prior_end]["val"])
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
            "gross_profit_tag": gp_tag,
            "cost_of_revenue": cost_in_billions,
            "cost_of_revenue_raw": cur_cost_val,
            "cost_label": f"${cost_in_billions}B" if cost_in_billions is not None else None,
            "cost_tag": cost_tag_used or cost_tag,
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
            "primary_driver": None,
            "driver_source": None,
            "driver_period": None,
            "driver_accession": None,
            "cloud_ai_revenue": None,
            "sentiment": (
                f"FY {fy} (ended {period_end}): Revenue ${rev_in_billions}B"
                + (f", YoY {growth_yoy:+}%" if growth_yoy is not None else "")
                + (f", Gross Margin {gross_margin}%" if gross_margin is not None else "")
            ),
            "reason": None,
        }


class Form10KParser:
    """Extracts Items 1, 1A, 7, 8 from Form 10-K primary document HTML/text."""

    @staticmethod
    def html_to_clean_text(html_content: str) -> str:
        """Strips HTML formatting, scripts, and normalizes whitespace."""
        soup = BeautifulSoup(html_content, "lxml")
        for tag in soup(["script", "style", "table", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        clean_lines = [line for line in lines if line]
        return "\n".join(clean_lines)

    @classmethod
    def extract_items(cls, text: str) -> dict[str, str]:
        """Extracts Item 1, Item 1A, Item 7, Item 8 text blocks.

        Handles drop caps, broken words, and avoids table of contents.
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

        # Slicing Item 8
        if m8:
            s8 = m8[-1].start()
            end_8 = re.search(
                r"(?:^|\n)\s*(?:ITEM\s+9\.?|Item\s+9\.?)",
                text[s8 + 100:],
                re.IGNORECASE,
            )
            e8 = s8 + 100 + end_8.start() if end_8 else s8 + 60000
            results["Item 8"] = text[s8:e8].strip()

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

        # 1. Company Facts (XBRL)
        facts = self.client.get_company_facts(cik)
        metrics = self.xbrl_parser.parse_metrics(clean_ticker, facts)

        # 2. Submissions
        submissions = self.client.get_submissions(cik)
        submission_10k = self.find_latest_10k_submission(submissions)
        accn = submission_10k["accessionNumber"]
        primary_doc = submission_10k["primaryDocument"]

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
