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
            # Look for structured lines produced by SEC ingestion or filing summaries
            rev_match = re.search(
                r"Total Revenue(?:\s*\(TTM\))?:\s*\$?([\d.]+)\s*Billion",
                content,
                re.IGNORECASE,
            )
            growth_match = re.search(
                r"Revenue Growth(?:\s*\(YoY\))?:\s*([+-]?[\d.]+)%",
                content,
                re.IGNORECASE,
            )
            margin_match = re.search(
                r"Gross Margin:\s*([\d.]+)%",
                content,
                re.IGNORECASE,
            )
            industry_match = re.search(
                r"Industry:\s*([^|\n]+)",
                content,
                re.IGNORECASE,
            )

            rev_val = float(rev_match.group(1)) if rev_match else None
            growth_val = float(growth_match.group(1)) if growth_match else None
            margin_val = float(margin_match.group(1)) if margin_match else None
            industry = industry_match.group(1).strip() if industry_match else None

            if any(v is not None for v in (rev_val, growth_val, margin_val)):
                return {
                    "source": "ingested_document",
                    "revenue": rev_val,
                    "revenue_label": f"${rev_val}B" if rev_val is not None else "N/A",
                    "growth_yoy": growth_val,
                    "growth_label": (
                        f"{growth_val:+}%" if growth_val is not None else "N/A"
                    ),
                    "gross_margin": margin_val,
                    "margin_label": (
                        f"{margin_val}%" if margin_val is not None else "N/A"
                    ),
                    "primary_driver": industry,
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

            return {
                "source": "yfinance (cached, optional)",
                "revenue": rev_val,
                "revenue_label": f"${rev_val}B" if rev_val is not None else "N/A",
                "growth_yoy": growth_val,
                "growth_label": (
                    f"{growth_val:+}%" if growth_val is not None else "N/A"
                ),
                "gross_margin": gm_val,
                "margin_label": f"{gm_val}%" if gm_val is not None else "N/A",
                "primary_driver": industry,
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
            "revenue": None,
            "revenue_label": "N/A",
            "growth_yoy": None,
            "growth_label": "N/A",
            "gross_margin": None,
            "margin_label": "N/A",
            "primary_driver": None,
            "cloud_ai_revenue": None,
            "sentiment": None,
            "reason": (
                f"No filing metrics or market data available for ticker '{clean}'."
            ),
        }
        self._cache[clean] = (now, empty_result)
        return empty_result


metrics_service = MetricsService()

