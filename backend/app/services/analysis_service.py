from fastapi import HTTPException

from app.core.config import settings
from app.core.logger import logger
from app.schemas.analysis import (
    AnalysisResponse,
    ComparisonResponse,
    CustomQueryResponse,
    SourceEvidenceNode,
)
from app.services.metrics_service import metrics_service
from app.services.rag_engine import rag_engine_service


class AnalysisService:
    """Orchestrates financial research inquiries, comparative evaluations, and custom queries.

    Uses metrics_service for grounded data and rag_engine_service for grounded citation RAG.
    """

    @staticmethod
    def _extract_sources(response) -> list[SourceEvidenceNode]:
        """Extracts source node snippets, relevance scores, and metadata from RAG response."""
        sources: list[SourceEvidenceNode] = []
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

    def analyze_single_stock(
        self,
        ticker: str,
        custom_prompt: str | None = None,
        groq_api_key: str | None = None,
    ) -> AnalysisResponse:
        """Executes a deep-dive financial analysis for a single stock with ticker filtering."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            raise HTTPException(
                status_code=400, detail="Stock ticker symbol is required."
            )

        file_path = settings.ARTICLES_DIR / f"{clean_ticker}.txt"
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No documents ingested for {clean_ticker} yet. Add one in the Filings tab.",
            )

        # Apply ticker metadata filter to prevent cross-stock contamination
        engine = rag_engine_service.get_query_engine(
            override_key=groq_api_key,
            ticker=clean_ticker,
        )

        prompt = (
            custom_prompt.strip()
            if custom_prompt and custom_prompt.strip()
            else (
                f"Generate an institutional financial analysis report for ticker {clean_ticker}. "
                "Evaluate revenue trajectory, core operating drivers, cloud/AI positioning, and risk factors "
                "based strictly on the retrieved context."
            )
        )

        try:
            logger.info(f"Executing single stock query for: {clean_ticker}")
            response = engine.query(prompt)
            metrics = metrics_service.get_metrics(clean_ticker)

            return AnalysisResponse(
                ticker=clean_ticker,
                prompt=prompt,
                report=str(response),
                sentiment=metrics.get("sentiment"),
                metrics=metrics,
                sources=self._extract_sources(response),
                is_sample=False,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Single stock analysis query failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Analysis query failed: {str(e)}"
            )

    def compare_stocks(
        self,
        stock_a: str,
        stock_b: str,
        custom_prompt: str | None = None,
        groq_api_key: str | None = None,
    ) -> ComparisonResponse:
        """Executes a comparative head-to-head analysis between two stocks."""
        clean_a = stock_a.strip().upper()
        clean_b = stock_b.strip().upper()
        if not clean_a or not clean_b:
            raise HTTPException(
                status_code=400,
                detail="Both stock tickers are required for comparison.",
            )

        missing = []
        if not (settings.ARTICLES_DIR / f"{clean_a}.txt").exists():
            missing.append(clean_a)
        if not (settings.ARTICLES_DIR / f"{clean_b}.txt").exists():
            missing.append(clean_b)

        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"No documents ingested for {', '.join(missing)} yet. Add one in the Filings tab.",
            )

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
            logger.info(
                f"Executing comparative analysis between {clean_a} and {clean_b}"
            )
            response = engine.query(prompt)

            meta_a = metrics_service.get_metrics(clean_a)
            meta_b = metrics_service.get_metrics(clean_b)

            comparison_chart_data = [
                {
                    "metric": "Revenue ($B)",
                    clean_a: meta_a.get("revenue"),
                    clean_b: meta_b.get("revenue"),
                    "source": meta_a.get("revenue_source") or "Yahoo Finance snapshot",
                    "period": meta_a.get("revenue_period") or "period not stated",
                },
                {
                    "metric": "YoY Growth (%)",
                    clean_a: meta_a.get("growth_yoy"),
                    clean_b: meta_b.get("growth_yoy"),
                    "source": meta_a.get("growth_source") or "Yahoo Finance snapshot",
                    "period": meta_a.get("growth_period") or "period not stated",
                },
                {
                    "metric": "Gross Margin (%)",
                    clean_a: meta_a.get("gross_margin"),
                    clean_b: meta_b.get("gross_margin"),
                    "source": meta_a.get("margin_source") or "Yahoo Finance snapshot",
                    "period": meta_a.get("margin_period") or "period not stated",
                },
            ]

            return ComparisonResponse(
                stock_a=clean_a,
                stock_b=clean_b,
                prompt=prompt,
                report=str(response),
                comparison_metrics=comparison_chart_data,
                sources=self._extract_sources(response),
                is_sample=False,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Comparative analysis query failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Comparative analysis failed: {str(e)}"
            )

    def custom_query(
        self,
        prompt: str,
        groq_api_key: str | None = None,
    ) -> CustomQueryResponse:
        """Executes a free-form semantic query across the financial corpus."""
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise HTTPException(status_code=400, detail="Query prompt cannot be empty.")

        if not settings.ARTICLES_DIR.exists() or not any(
            settings.ARTICLES_DIR.glob("*.txt")
        ):
            raise HTTPException(
                status_code=404,
                detail="No documents ingested yet. Add one in the Filings tab.",
            )

        engine = rag_engine_service.get_query_engine(override_key=groq_api_key)

        try:
            logger.info(f"Executing custom inquiry: {clean_prompt[:60]}...")
            response = engine.query(clean_prompt)
            return CustomQueryResponse(
                prompt=clean_prompt,
                report=str(response),
                sources=self._extract_sources(response),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Custom query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


analysis_service = AnalysisService()
