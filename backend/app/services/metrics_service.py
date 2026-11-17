import re
import time
from typing import Any

from app.core.config import settings
from app.core.logger import logger


class MetricsService:
    """Provides grounded financial metrics extracted from ingested documents or

    clearly-labeled, cached, optional yfinance market feeds.
    Returns null values plus a reason when real data is missing.
    No hard-coded metrics, no invented default sentiment.
    """

    def __init__(self, cache_ttl_seconds: int = 3600):
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def _parse_from_ingested_file(self, ticker: str) -> dict[str, Any] | None:
        """Attempts to parse verifiable financial metrics from saved filing text in articles/."""
        clean = ticker.upper()
        file_path = settings.ARTICLES_DIR / f"{clean}.txt"
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            is_sec = bool(
                re.search(
                    r"\b(10-K|10-Q|SEC EDGAR|Form 10-K|Securities and Exchange Commission)\b",
                    content,
                    re.IGNORECASE,
                )
            )
            doc_source = "SEC filing" if is_sec else "Yahoo Finance snapshot"

            # Parse Revenue & Period
            rev_match = re.search(
                r"Total Revenue(?:\s*\(([^)]+)\))?:\s*\$?([\d.]+)\s*Billion",
                content,
                re.IGNORECASE,
            )
            rev_period = "period not stated"
            rev_val = None
            if rev_match:
                rev_period = (
                    rev_match.group(1).strip()
                    if rev_match.group(1)
                    else "period not stated"
                )
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
                r"(?:Quarterly\s+)?Revenue Growth(?:\s*\(([^)]+)\))?:\s*([+-]?[\d.]+)%",
                content,
                re.IGNORECASE,
            )
            growth_period = "period not stated"
            growth_val = None
            if growth_match:
                growth_period = (
                    growth_match.group(1).strip() if growth_match.group(1) else "YoY"
                )
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
            margin_period = "period not stated"
            margin_val = None
            if margin_match:
                margin_period = (
                    margin_match.group(1).strip()
                    if margin_match.group(1)
                    else "period not stated"
                )
                margin_val = float(margin_match.group(2))
            else:
                alt_margin = re.search(
                    r"Gross margin(?:\s*\w+)*\s*([\d.]+)%",
                    content,
                    re.IGNORECASE,
                )
                if alt_margin:
                    margin_val = float(alt_margin.group(1))
                    margin_period = "period not stated"

            # Parse Primary Driver / Industry
            industry_match = re.search(
                r"Industry:\s*([^|\n]+)",
                content,
                re.IGNORECASE,
            )
            industry = industry_match.group(1).strip() if industry_match else None
            if not industry:
                # Check for segment mentions like Data Center or Cloud
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
                    "source_badge": "From ingested document",
                    "revenue": rev_val,
                    "revenue_label": f"${rev_val}B" if rev_val is not None else "N/A",
                    "revenue_source": doc_source,
                    "revenue_period": rev_period,
                    "growth_yoy": growth_val,
                    "growth_label": (
                        f"{growth_val:+}%" if growth_val is not None else "N/A"
                    ),
                    "growth_source": doc_source,
                    "growth_period": growth_period,
                    "gross_margin": margin_val,
                    "margin_label": (
                        f"{margin_val}%" if margin_val is not None else "N/A"
                    ),
                    "margin_source": doc_source,
                    "margin_period": margin_period,
                    "primary_driver": industry,
                    "driver_source": doc_source,
                    "driver_period": "period not stated",
                    "cloud_ai_revenue": None,
                    "sentiment": None,
                    "reason": None,
                }
        except Exception as e:
            logger.warning(
                f"Failed to parse structured metrics from filing {clean}.txt: {e}"
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
                "revenue": rev_val,
                "revenue_label": f"${rev_val}B" if rev_val is not None else "N/A",
                "revenue_source": doc_source,
                "revenue_period": "TTM",
                "growth_yoy": growth_val,
                "growth_label": (
                    f"{growth_val:+}%" if growth_val is not None else "N/A"
                ),
                "growth_source": doc_source,
                "growth_period": "Quarterly YoY",
                "gross_margin": gm_val,
                "margin_label": f"{gm_val}%" if gm_val is not None else "N/A",
                "margin_source": doc_source,
                "margin_period": "period not stated",
                "primary_driver": industry,
                "driver_source": doc_source,
                "driver_period": "period not stated",
                "cloud_ai_revenue": None,
                "sentiment": None,
                "reason": None,
            }
        except Exception as e:
            logger.info(f"Optional yfinance lookup skipped/failed for {clean}: {e}")
            return None

    def get_metrics(self, ticker: str) -> dict[str, Any]:
        """Returns structured financial metrics if real data exists.

        Otherwise returns null values plus an explicit reason. Sentiment is null unless computed.
        """
        clean = ticker.strip().upper()
        now = time.time()

        # Check memory cache
        if clean in self._cache:
            ts, data = self._cache[clean]
            if now - ts < self._cache_ttl:
                return data

        # 1. Attempt parsing from ingested document
        parsed = self._parse_from_ingested_file(clean)
        if parsed:
            self._cache[clean] = (now, parsed)
            return parsed

        # 2. Attempt optional yfinance source
        yf_data = self._fetch_from_yfinance(clean)
        if yf_data:
            self._cache[clean] = (now, yf_data)
            return yf_data

        # 3. Grounded fallback: null values + truthful reason
        empty_result = {
            "source": None,
            "source_label": "Unknown",
            "source_badge": "Data Absent",
            "revenue": None,
            "revenue_label": "N/A",
            "revenue_source": "period not stated",
            "revenue_period": "period not stated",
            "growth_yoy": None,
            "growth_label": "N/A",
            "growth_source": "period not stated",
            "growth_period": "period not stated",
            "gross_margin": None,
            "margin_label": "N/A",
            "margin_source": "period not stated",
            "margin_period": "period not stated",
            "primary_driver": None,
            "driver_source": "period not stated",
            "driver_period": "period not stated",
            "cloud_ai_revenue": None,
            "sentiment": None,
            "reason": (
                f"No filing metrics or market data available for ticker '{clean}'."
            ),
        }
        self._cache[clean] = (now, empty_result)
        return empty_result


metrics_service = MetricsService()
