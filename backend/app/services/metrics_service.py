import json
import re
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logger import logger


class MetricsService:
    """Provides grounded financial metrics extracted from audited SEC filings,

    ingested documents, or clearly-labeled cached yfinance market feeds.
    Returns null values plus a reason when real data is missing.
    No hard-coded metrics, no invented default sentiment, no guessed periods.
    """

    def __init__(self, cache_ttl_seconds: int = 3600):
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def _load_sec_metrics_store(self) -> dict[str, Any]:
        """Loads persisted SEC XBRL metrics store if available."""
        if settings.SEC_METRICS_FILE.exists():
            try:
                return json.loads(settings.SEC_METRICS_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Could not load SEC metrics store: {e}")
        return {}

    def _find_ticker_article_files(self, clean_ticker: str) -> list[Path]:
        """Finds all article files for a ticker, prioritizing official 10-K filings."""
        if not settings.ARTICLES_DIR.exists():
            return []
        files = list(settings.ARTICLES_DIR.glob(f"{clean_ticker}*.txt")) + list(
            settings.ARTICLES_DIR.glob(f"{clean_ticker}*.md")
        )
        # Prioritize _10K files first
        files.sort(key=lambda p: (0 if "_10K" in p.name or "_10k" in p.name else 1, p.name))
        return files

    def _parse_from_ingested_file(self, ticker: str) -> dict[str, Any] | None:
        """Attempts to parse verifiable financial metrics from saved filing text in articles/."""
        clean = ticker.upper()
        matching_files = self._find_ticker_article_files(clean)
        if not matching_files:
            return None

        file_path = matching_files[0]

        try:
            content = file_path.read_text(encoding="utf-8")

            # Determine document source truthfully (Requirement 4)
            if "[DOCUMENT_METADATA]" in content and "Source: SEC EDGAR" in content:
                doc_source = "SEC filing"
                source_badge = "SEC filing (XBRL)"
            elif "[DOCUMENT_SOURCE: SEC EDGAR]" in content:
                doc_source = "SEC filing"
                source_badge = "SEC filing (XBRL)"
            elif (
                "[DOCUMENT_SOURCE: Yahoo Finance snapshot (undated)]" in content
                or "(Yahoo Finance snapshot (undated))" in content
            ):
                doc_source = "Yahoo Finance snapshot (undated)"
                source_badge = "From Yahoo Finance snapshot (undated)"
            elif "[DOCUMENT_SOURCE: Yahoo Finance snapshot]" in content:
                doc_source = "Yahoo Finance snapshot"
                source_badge = "From Yahoo Finance snapshot"
            elif "Financial & Corporate Overview" in content and "Sector:" in content:
                # Undated Yahoo Finance snapshot format
                doc_source = "Yahoo Finance snapshot (undated)"
                source_badge = "From Yahoo Finance snapshot (undated)"
            else:
                # Any other ingested document or pasted notes
                doc_source = "Hand-written summary"
                source_badge = "From hand-written summary"

            # Parse metadata header if present
            accn = None
            period_end = None
            fy = None
            accn_match = re.search(r"Accession Number:\s*([0-9-]+)", content)
            if accn_match:
                accn = accn_match.group(1).strip()
            period_end_match = re.search(r"Period End Date:\s*([0-9-]+)", content)
            if period_end_match:
                period_end = period_end_match.group(1).strip()
            fy_match = re.search(r"Fiscal Year:\s*(\d{4})", content)
            if fy_match:
                fy = int(fy_match.group(1).strip())

            # Parse Revenue & Period
            rev_match = re.search(
                r"Total Revenue(?:\s*\(([^)]+)\))?:\s*\$?([\d.]+)\s*Billion",
                content,
                re.IGNORECASE,
            )
            rev_period = f"FY {fy} (ended {period_end})" if fy and period_end else "period not stated"
            rev_val = None
            if rev_match:
                if rev_match.group(1):
                    rev_period = rev_match.group(1).strip()
                rev_val = float(rev_match.group(2))
            else:
                alt_rev = re.search(
                    r"(?:(Q[1-4]|FY\s*\d{2,4}|full year)\s+)?revenue(?:\s+(?:of|reached))?\s*\$?([\d.]+)\s*(?:billion|B)",
                    content,
                    re.IGNORECASE,
                )
                if alt_rev:
                    if alt_rev.group(1):
                        rev_period = alt_rev.group(1).strip()
                    rev_val = float(alt_rev.group(2))

            # Parse Growth & Period
            growth_match = re.search(
                r"(?:Quarterly\s+)?(?:YoY\s+)?Revenue Growth(?:\s*\(([^)]+)\))?:\s*([+-]?[\d.]+)%",
                content,
                re.IGNORECASE,
            )
            growth_period = f"FY {fy} vs prior (ended {period_end})" if fy and period_end else "period not stated"
            growth_val = None
            if growth_match:
                if growth_match.group(1):
                    growth_period = growth_match.group(1).strip()
                growth_val = float(growth_match.group(2))
            else:
                alt_growth = re.search(
                    r"(?:up|grew|increased by|increase of)\s*([+-]?[\d.]+)%\s*(?:(?:from|over)\s+(?:a\s+year\s+ago|prior-year|prior\s+year))?",
                    content,
                    re.IGNORECASE,
                )
                if alt_growth:
                    growth_val = float(alt_growth.group(1))
                    growth_period = "YoY"

            # Parse Margin & Period
            margin_match = re.search(
                r"Gross Margin(?:\s*\(([^)]+)\))?:\s*([\d.]+)%",
                content,
                re.IGNORECASE,
            )
            margin_period = f"FY {fy} (ended {period_end})" if fy and period_end else "period not stated"
            margin_val = None
            if margin_match:
                if margin_match.group(1):
                    margin_period = margin_match.group(1).strip()
                margin_val = float(margin_match.group(2))
            else:
                alt_margin = re.search(
                    r"Gross margin(?:\s*\w+)*\s*([\d.]+)%",
                    content,
                    re.IGNORECASE,
                )
                if alt_margin:
                    margin_val = float(alt_margin.group(1))

            # Parse Primary Driver / Industry
            industry_match = re.search(r"Industry:\s*([^|\n]+)", content, re.IGNORECASE)
            industry = industry_match.group(1).strip() if industry_match else None
            if not industry:
                seg_match = re.search(
                    r"\b(Data Center|Cloud|Personal Computing|Semiconductors)\b",
                    content,
                    re.IGNORECASE,
                )
                if seg_match:
                    industry = seg_match.group(1).strip()

            if any(v is not None for v in (rev_val, growth_val, margin_val)):
                return {
                    "source": doc_source,
                    "source_label": doc_source,
                    "source_badge": source_badge,
                    "fiscal_year": fy,
                    "period_end_date": period_end,
                    "accession_number": accn,
                    "revenue": rev_val,
                    "revenue_label": f"${rev_val}B" if rev_val is not None else "N/A",
                    "revenue_source": doc_source,
                    "revenue_period": rev_period,
                    "revenue_accession": accn,
                    "growth_yoy": growth_val,
                    "growth_label": f"{growth_val:+}%" if growth_val is not None else "N/A",
                    "growth_source": doc_source,
                    "growth_period": growth_period,
                    "growth_accession": accn,
                    "gross_margin": margin_val,
                    "margin_label": f"{margin_val}%" if margin_val is not None else "N/A",
                    "margin_source": doc_source,
                    "margin_period": margin_period,
                    "margin_accession": accn,
                    "primary_driver": industry or f"Ingested Document ({clean})",
                    "driver_source": doc_source,
                    "driver_period": rev_period,
                    "driver_accession": accn,
                    "cloud_ai_revenue": None,
                    "sentiment": None,
                    "reason": None,
                }
        except Exception as e:
            logger.warning(
                f"Failed to parse structured metrics from filing {file_path.name}: {e}"
            )

        return None

    def _fetch_from_yfinance(self, ticker: str) -> dict[str, Any] | None:
        """Fetches optional, clearly-labeled, cached financial ratios from Yahoo Finance."""
        clean = ticker.upper()
        try:
            import yfinance as yf

            stock = yf.Ticker(clean)
            info = stock.info
            if not info or not info.get("shortName"):
                return None

            rev = info.get("totalRevenue")
            rev_val = round(rev / 1e9, 2) if rev else None

            growth = info.get("revenueGrowth")
            growth_val = round(growth * 100, 1) if growth is not None else None

            gm = info.get("grossMargins")
            gm_val = round(gm * 100, 1) if gm is not None else None

            industry = info.get("industry")

            doc_source = "Yahoo Finance snapshot"
            return {
                "source": doc_source,
                "source_label": doc_source,
                "source_badge": "From Yahoo Finance snapshot",
                "fiscal_year": None,
                "period_end_date": None,
                "accession_number": None,
                "revenue": rev_val,
                "revenue_label": f"${rev_val}B" if rev_val is not None else "N/A",
                "revenue_source": doc_source,
                "revenue_period": "TTM",
                "revenue_accession": None,
                "growth_yoy": growth_val,
                "growth_label": f"{growth_val:+}%" if growth_val is not None else "N/A",
                "growth_source": doc_source,
                "growth_period": "Quarterly YoY",
                "growth_accession": None,
                "gross_margin": gm_val,
                "margin_label": f"{gm_val}%" if gm_val is not None else "N/A",
                "margin_source": doc_source,
                "margin_period": "period not stated",
                "margin_accession": None,
                "primary_driver": industry,
                "driver_source": doc_source,
                "driver_period": "period not stated",
                "driver_accession": None,
                "cloud_ai_revenue": None,
                "sentiment": None,
                "reason": None,
            }
        except Exception as e:
            logger.info(f"Optional yfinance lookup skipped/failed for {clean}: {e}")
            return None

    def get_metrics(self, ticker: str) -> dict[str, Any]:
        """Returns structured financial metrics if real data exists.

        1. Priority: Grounded SEC XBRL facts store (exact periods, accession numbers).
        2. Priority: Ingested file in articles/ (truthfully labeled: SEC filing, Yahoo snapshot, Hand-written summary).
        3. Priority: Live yfinance snapshot.
        4. Fallback: null values + truthful reason. Never defaults to 'Yahoo Finance snapshot'.
        """
        clean = ticker.strip().upper()
        now = time.time()

        # Check memory cache
        if clean in self._cache:
            ts, data = self._cache[clean]
            if now - ts < self._cache_ttl:
                return data

        # 1. Grounded SEC XBRL metrics store
        sec_store = self._load_sec_metrics_store()
        if clean in sec_store:
            data = sec_store[clean]
            self._cache[clean] = (now, data)
            return data

        # 2. Attempt parsing from ingested document
        parsed = self._parse_from_ingested_file(clean)
        if parsed:
            self._cache[clean] = (now, parsed)
            return parsed

        # 3. Attempt optional yfinance source
        yf_data = self._fetch_from_yfinance(clean)
        if yf_data:
            self._cache[clean] = (now, yf_data)
            return yf_data

        # 4. Grounded fallback: null values + truthful reason
        empty_result = {
            "source": None,
            "source_label": "Unknown",
            "source_badge": "Data Absent",
            "fiscal_year": None,
            "period_end_date": None,
            "accession_number": None,
            "revenue": None,
            "revenue_label": "N/A",
            "revenue_source": None,
            "revenue_period": "period not stated",
            "revenue_accession": None,
            "growth_yoy": None,
            "growth_label": "N/A",
            "growth_source": None,
            "growth_period": "period not stated",
            "growth_accession": None,
            "gross_margin": None,
            "margin_label": "N/A",
            "margin_source": None,
            "margin_period": "period not stated",
            "margin_accession": None,
            "primary_driver": None,
            "driver_source": None,
            "driver_period": "period not stated",
            "driver_accession": None,
            "cloud_ai_revenue": None,
            "sentiment": None,
            "reason": (
                f"No filing metrics or market data available for ticker '{clean}'."
            ),
        }
        self._cache[clean] = (now, empty_result)
        return empty_result


metrics_service = MetricsService()
