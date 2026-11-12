from typing import List, Optional
from fastapi import HTTPException

from app.core.logger import logger
from app.schemas.analysis import (
    AnalysisResponse,
    ComparisonResponse,
    CustomQueryResponse,
    SourceEvidenceNode,
)
from app.services.rag_engine import rag_engine_service


class AnalysisService:
    """Orchestrates financial research inquiries, comparative evaluations, and custom queries."""

    @staticmethod
    def _extract_sources(response) -> List[SourceEvidenceNode]:
        """Extracts source node snippets, relevance scores, and metadata from RAG response."""
        sources: List[SourceEvidenceNode] = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                text = node.node.get_text()
                snippet = text[:320] + "..." if len(text) > 320 else text
                sources.append(
                    SourceEvidenceNode(
                        score=getattr(node, "score", None),
                        text=snippet,
                        metadata=getattr(node.node, "metadata", {}),
                    )
                )
        return sources

    @staticmethod
    def _extract_metrics(ticker: str) -> dict:
        """Returns structured benchmark metrics for visual chart rendering."""
        benchmarks = {
            "NVDA": {
                "revenue": 22.1,
                "revenue_label": "$22.1B",
                "growth_yoy": 265,
                "growth_label": "+265%",
                "gross_margin": 76.0,
                "margin_label": "76.0%",
                "primary_driver": "H100 Tensor GPUs & Hopper",
                "cloud_ai_revenue": "$18.4B (Data Center)",
                "sentiment": "Strong Bullish",
            },
            "GOOGL": {
                "revenue": 86.3,
                "revenue_label": "$86.3B",
                "growth_yoy": 13,
                "growth_label": "+13%",
                "gross_margin": 56.5,
                "margin_label": "56.5%",
                "primary_driver": "Search & YouTube Ads",
                "cloud_ai_revenue": "$9.19B (Google Cloud)",
                "sentiment": "Moderate Bullish",
            },
            "AAPL": {
                "revenue": 119.6,
                "revenue_label": "$119.6B",
                "growth_yoy": 2,
                "growth_label": "+2%",
                "gross_margin": 45.9,
                "margin_label": "45.9%",
                "primary_driver": "iPhone 15 & Services",
                "cloud_ai_revenue": "Apple Intelligence & Silicon",
                "sentiment": "Neutral / Steady",
            },
            "MSFT": {
                "revenue": 62.0,
                "revenue_label": "$62.0B",
                "growth_yoy": 18,
                "growth_label": "+18%",
                "gross_margin": 68.4,
                "margin_label": "68.4%",
                "primary_driver": "Azure Cloud & Copilot",
                "cloud_ai_revenue": "$33.7B (Microsoft Cloud)",
                "sentiment": "Strong Bullish",
            },
        }
        clean = ticker.upper()
        if clean in benchmarks:
            return benchmarks[clean]

        # Dynamic fallback to yfinance for any stock in the world
        try:
            import yfinance as yf
            t = yf.Ticker(clean)
            info = t.info
            rev = info.get("totalRevenue")
            rev_val = round(rev / 1e9, 1) if rev else None
            growth = info.get("revenueGrowth")
            growth_val = round(growth * 100, 1) if growth is not None else None
            gm = info.get("grossMargins")
            gm_val = round(gm * 100, 1) if gm is not None else None

            return {
                "revenue": rev_val,
                "revenue_label": f"${rev_val}B" if rev_val else "N/A",
                "growth_yoy": growth_val,
                "growth_label": f"{growth_val:+}%" if growth_val is not None else "N/A",
                "gross_margin": gm_val,
                "margin_label": f"{gm_val}%" if gm_val is not None else "N/A",
                "primary_driver": info.get("industry") or "Corporate Operations",
                "cloud_ai_revenue": f"Market Cap: ${round(info.get('marketCap', 0) / 1e9, 1)}B",
                "sentiment": "Moderate Bullish" if (growth_val or 0) > 0 else "Neutral",
            }
        except Exception:
            return {
                "revenue": None,
                "revenue_label": "N/A",
                "growth_yoy": None,
                "growth_label": "N/A",
                "gross_margin": None,
                "margin_label": "N/A",
                "primary_driver": "Extracted from filing",
                "cloud_ai_revenue": "See report context",
                "sentiment": "Bullish",
            }

    def analyze_single_stock(
        self,
        ticker: str,
        custom_prompt: Optional[str] = None,
        groq_api_key: Optional[str] = None,
    ) -> AnalysisResponse:
        """Executes a deep-dive financial analysis for a single stock."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            raise HTTPException(status_code=400, detail="Stock ticker symbol is required.")

        engine = rag_engine_service.get_query_engine(override_key=groq_api_key)

        prompt = (
            custom_prompt.strip()
            if custom_prompt and custom_prompt.strip()
            else (
                f"Generate a comprehensive financial analysis report for ticker {clean_ticker}. "
                "Highlight revenue trajectory, growth drivers, cloud/AI positioning, and risk factors "
                "based strictly on the retrieved context."
            )
        )

        try:
            logger.info(f"Executing single stock query for: {clean_ticker}")
            response = engine.query(prompt)
            metrics = self._extract_metrics(clean_ticker)

            return AnalysisResponse(
                ticker=clean_ticker,
                prompt=prompt,
                report=str(response),
                sentiment=metrics.get("sentiment", "Bullish"),
                metrics=metrics,
                sources=self._extract_sources(response),
            )
        except Exception as e:
            logger.error(f"Single stock analysis query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Analysis query failed: {str(e)}")

    def compare_stocks(
        self,
        stock_a: str,
        stock_b: str,
        custom_prompt: Optional[str] = None,
        groq_api_key: Optional[str] = None,
    ) -> ComparisonResponse:
        """Executes a comparative head-to-head analysis between two stocks."""
        clean_a = stock_a.strip().upper()
        clean_b = stock_b.strip().upper()
        if not clean_a or not clean_b:
            raise HTTPException(status_code=400, detail="Both stock tickers are required for comparison.")

        engine = rag_engine_service.get_query_engine(override_key=groq_api_key)

        prompt = (
            custom_prompt.strip()
            if custom_prompt and custom_prompt.strip()
            else (
                f"Conduct a side-by-side comparative financial analysis between {clean_a} and {clean_b}. "
                "Compare revenue growth rates, key product drivers, market opportunities, and primary risk factors "
                "based strictly on the retrieved context."
            )
        )

        try:
            logger.info(f"Executing comparative analysis between {clean_a} and {clean_b}")
            response = engine.query(prompt)

            meta_a = self._extract_metrics(clean_a)
            meta_b = self._extract_metrics(clean_b)

            comparison_chart_data = [
                {
                    "metric": "Revenue ($B)",
                    clean_a: meta_a.get("revenue") or 0,
                    clean_b: meta_b.get("revenue") or 0,
                },
                {
                    "metric": "YoY Growth (%)",
                    clean_a: meta_a.get("growth_yoy") or 0,
                    clean_b: meta_b.get("growth_yoy") or 0,
                },
                {
                    "metric": "Gross Margin (%)",
                    clean_a: meta_a.get("gross_margin") or 0,
                    clean_b: meta_b.get("gross_margin") or 0,
                },
            ]

            return ComparisonResponse(
                stock_a=clean_a,
                stock_b=clean_b,
                prompt=prompt,
                report=str(response),
                comparison_metrics=comparison_chart_data,
                sources=self._extract_sources(response),
            )
        except Exception as e:
            logger.error(f"Comparative analysis query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Comparative analysis failed: {str(e)}")

    def custom_query(
        self,
        prompt: str,
        groq_api_key: Optional[str] = None,
    ) -> CustomQueryResponse:
        """Executes a free-form semantic query across the financial corpus."""
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise HTTPException(status_code=400, detail="Query prompt cannot be empty.")

        engine = rag_engine_service.get_query_engine(override_key=groq_api_key)

        try:
            logger.info(f"Executing custom inquiry: {clean_prompt[:60]}...")
            response = engine.query(clean_prompt)
            return CustomQueryResponse(
                prompt=clean_prompt,
                report=str(response),
                sources=self._extract_sources(response),
            )
        except Exception as e:
            logger.error(f"Custom query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


analysis_service = AnalysisService()

