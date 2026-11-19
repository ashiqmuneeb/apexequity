import re

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
from app.services.number_validator import number_validator
from app.services.rag_engine import QA_PROMPT_TEMPLATE, rag_engine_service
from app.services.retrieval_service import retrieval_service
from app.services.sec_service import format_verified_facts


KNOWN_TICKERS = {"NVDA", "MSFT", "AAPL", "GOOGL", "AMD"}
COMPANY_TICKER_MAP = {
    "nvidia": "NVDA",
    "microsoft": "MSFT",
    "apple": "AAPL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amd": "AMD",
    "advanced micro devices": "AMD",
}


class AnalysisService:
    """Orchestrates institutional financial research reports, comparative head-to-head evaluations,

    and custom semantic queries grounded by audited XBRL facts and hybrid retrieval.
    """

    @staticmethod
    def _format_source_passage(idx: int, src: SourceEvidenceNode) -> str:
        """Formats a single source passage with citation index and filing metadata."""
        meta_parts = []
        if src.section:
            meta_parts.append(f"Section: {src.section}")
        if src.form:
            meta_parts.append(f"Form: {src.form}")
        if src.fiscal_year:
            meta_parts.append(f"Fiscal Year: {src.fiscal_year}")
        if src.accession_number:
            meta_parts.append(f"Accession: {src.accession_number}")

        header = f"[{idx}] Source: {src.ticker} 10-K (" + ", ".join(meta_parts) + ")"
        return f"{header}\n{src.quote}"

    def analyze_single_stock(
        self,
        ticker: str,
        custom_prompt: str | None = None,
        groq_api_key: str | None = None,
    ) -> AnalysisResponse:
        """Executes a deep-dive financial analysis for a single stock with audited XBRL facts injection."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            raise HTTPException(
                status_code=400, detail="Stock ticker symbol is required."
            )

        ticker_files = list(settings.ARTICLES_DIR.glob(f"{clean_ticker}*.txt")) + list(
            settings.ARTICLES_DIR.glob(f"{clean_ticker}*.md")
        )
        if not ticker_files:
            raise HTTPException(
                status_code=404,
                detail=f"No documents ingested for {clean_ticker} yet. Add one in the Filings tab.",
            )

        # 1. Fetch structured audited XBRL facts
        metrics = metrics_service.get_metrics(clean_ticker)
        facts_block = format_verified_facts(metrics)

        # 2. Hybrid retrieval strictly filtered by ticker
        prompt = (
            custom_prompt.strip()
            if custom_prompt and custom_prompt.strip()
            else (
                f"Generate an institutional financial analysis report for ticker {clean_ticker}. "
                "Evaluate revenue trajectory, core operating drivers, cloud/AI positioning, and risk factors "
                "based strictly on the retrieved context."
            )
        )

        sources = retrieval_service.retrieve_single(clean_ticker, prompt, top_n=5)

        # 3. Assemble prompt context
        passages = [
            self._format_source_passage(i + 1, src) for i, src in enumerate(sources)
        ]
        context_str = f"{facts_block}\n\n=== RETRIEVED SOURCES ===\n" + "\n\n".join(passages)
        full_prompt = QA_PROMPT_TEMPLATE.format(context_str=context_str, query_str=prompt)

        try:
            logger.info(f"Executing single stock query for: {clean_ticker}")
            raw_answer = rag_engine_service.generate_completion(
                full_prompt, override_key=groq_api_key
            )

            # Refusal check
            if "not disclosed in the retrieved filings" in raw_answer.lower():
                return AnalysisResponse(
                    ticker=clean_ticker,
                    prompt=prompt,
                    report="Not disclosed in the retrieved filings.",
                    sentiment=metrics.get("sentiment"),
                    metrics=metrics,
                    sources=sources,
                    unsupported_numbers=[],
                    is_sample=False,
                )

            # 4. Number Grounding Validation
            source_texts = [s.quote for s in sources]
            validated_report, unsupported = number_validator.validate(
                raw_answer, facts_block, metrics, source_texts
            )

            return AnalysisResponse(
                ticker=clean_ticker,
                prompt=prompt,
                report=validated_report,
                sentiment=metrics.get("sentiment"),
                metrics=metrics,
                sources=sources,
                unsupported_numbers=unsupported,
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
        """Executes a comparative head-to-head analysis between two stocks with strict filing isolation."""
        clean_a = stock_a.strip().upper()
        clean_b = stock_b.strip().upper()
        if not clean_a or not clean_b:
            raise HTTPException(
                status_code=400,
                detail="Both stock tickers are required for comparison.",
            )

        missing = []
        for sym in [clean_a, clean_b]:
            files = list(settings.ARTICLES_DIR.glob(f"{sym}*.txt")) + list(
                settings.ARTICLES_DIR.glob(f"{sym}*.md")
            )
            if not files:
                missing.append(sym)

        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"No documents ingested for {', '.join(missing)} yet. Add one in the Filings tab.",
            )

        prompt = (
            custom_prompt.strip()
            if custom_prompt and custom_prompt.strip()
            else (
                f"Conduct a side-by-side comparative financial analysis between {clean_a} and {clean_b}. "
                "Compare revenue growth rates, key product drivers, market opportunities, and primary risk factors "
                "based strictly on the retrieved context."
            )
        )

        # 1. Fetch structured XBRL facts for both stocks
        meta_a = metrics_service.get_metrics(clean_a)
        meta_b = metrics_service.get_metrics(clean_b)
        facts_a = format_verified_facts(meta_a)
        facts_b = format_verified_facts(meta_b)

        # 2. Strict isolated retrieval: 5 chunks per company
        sources_a, sources_b = retrieval_service.retrieve_compare(
            clean_a, clean_b, prompt, top_n=5
        )

        # Build numbered citations: [1]..[5] for stock A, [6]..[10] for stock B
        passages_a = [
            self._format_source_passage(i + 1, src) for i, src in enumerate(sources_a)
        ]
        offset = len(sources_a)
        passages_b = [
            self._format_source_passage(offset + i + 1, src)
            for i, src in enumerate(sources_b)
        ]

        all_sources = sources_a + sources_b

        context_str = (
            f"{facts_a}\n\n{facts_b}\n\n"
            f"=== RETRIEVED SOURCES FOR {clean_a} ===\n"
            + "\n\n".join(passages_a)
            + f"\n\n=== RETRIEVED SOURCES FOR {clean_b} ===\n"
            + "\n\n".join(passages_b)
        )

        full_prompt = QA_PROMPT_TEMPLATE.format(context_str=context_str, query_str=prompt)

        try:
            logger.info(
                f"Executing comparative analysis between {clean_a} and {clean_b}"
            )
            raw_answer = rag_engine_service.generate_completion(
                full_prompt, override_key=groq_api_key
            )

            # Refusal check
            if "not disclosed in the retrieved filings" in raw_answer.lower():
                report_text = "Not disclosed in the retrieved filings."
                unsupported = []
            else:
                combined_facts = f"{facts_a}\n\n{facts_b}"
                source_texts = [s.quote for s in all_sources]
                # Combined metrics for validator
                merged_metrics = {}
                for k, v in meta_a.items():
                    merged_metrics[f"{clean_a}_{k}"] = v
                for k, v in meta_b.items():
                    merged_metrics[f"{clean_b}_{k}"] = v

                report_text, unsupported = number_validator.validate(
                    raw_answer, combined_facts, merged_metrics, source_texts
                )

            comparison_chart_data = [
                {
                    "metric": "Revenue ($B)",
                    clean_a: meta_a.get("revenue"),
                    clean_b: meta_b.get("revenue"),
                    "source": meta_a.get("revenue_source") or meta_a.get("source") or "Unknown",
                    "period": meta_a.get("revenue_period") or "period not stated",
                },
                {
                    "metric": "YoY Growth (%)",
                    clean_a: meta_a.get("growth_yoy"),
                    clean_b: meta_b.get("growth_yoy"),
                    "source": meta_a.get("growth_source") or meta_a.get("source") or "Unknown",
                    "period": meta_a.get("growth_period") or "period not stated",
                },
                {
                    "metric": "Gross Margin (%)",
                    clean_a: meta_a.get("gross_margin"),
                    clean_b: meta_b.get("gross_margin"),
                    "source": meta_a.get("margin_source") or meta_a.get("source") or "Unknown",
                    "period": meta_a.get("margin_period") or "period not stated",
                },
            ]

            return ComparisonResponse(
                stock_a=clean_a,
                stock_b=clean_b,
                prompt=prompt,
                report=report_text,
                comparison_metrics=comparison_chart_data,
                sources=all_sources,
                unsupported_numbers=unsupported,
                is_sample=False,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Comparative analysis query failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Comparative analysis failed: {str(e)}"
            )

    @staticmethod
    def _detect_ticker_in_query(query: str) -> str | None:
        """Extracts primary ticker symbol from natural language query."""
        words = re.findall(r"\b[A-Za-z0-9_-]+\b", query)
        for w in words:
            up = w.upper()
            if up in KNOWN_TICKERS:
                return up
            low = w.lower()
            if low in COMPANY_TICKER_MAP:
                return COMPANY_TICKER_MAP[low]
        return None

    def custom_query(
        self,
        prompt: str,
        groq_api_key: str | None = None,
    ) -> CustomQueryResponse:
        """Executes a natural language query with ticker metadata filtering and strict refusal path."""
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise HTTPException(status_code=400, detail="Query prompt cannot be empty.")

        detected_ticker = self._detect_ticker_in_query(clean_prompt)
        facts_block = ""
        metrics = None

        if detected_ticker:
            try:
                metrics = metrics_service.get_metrics(detected_ticker)
                facts_block = format_verified_facts(metrics)
            except Exception as e:
                logger.debug(f"Could not load facts for detected ticker {detected_ticker}: {e}")

        # Retrieve relevant chunks
        if detected_ticker:
            sources = retrieval_service.retrieve_single(detected_ticker, clean_prompt, top_n=5)
        else:
            candidates = retrieval_service.retrieve_candidates_for_ticker("ALL", clean_prompt)
            sources = retrieval_service.rerank_and_select(clean_prompt, candidates, top_n=5)

        passages = [
            self._format_source_passage(i + 1, src) for i, src in enumerate(sources)
        ]
        context_str = (
            (facts_block + "\n\n" if facts_block else "")
            + "=== RETRIEVED SOURCES ===\n"
            + "\n\n".join(passages)
        )
        full_prompt = QA_PROMPT_TEMPLATE.format(context_str=context_str, query_str=clean_prompt)

        try:
            logger.info(f"Executing custom inquiry: {clean_prompt[:60]}...")
            raw_answer = rag_engine_service.generate_completion(
                full_prompt, override_key=groq_api_key
            )

            # Refusal check (Condition 8)
            clean_ans = raw_answer.strip()
            if (
                clean_ans.lower().startswith("not disclosed in the retrieved filings")
                or "not disclosed in the retrieved filings" in clean_ans.lower()
            ):
                return CustomQueryResponse(
                    prompt=clean_prompt,
                    report="Not disclosed in the retrieved filings.",
                    sources=sources,
                    unsupported_numbers=[],
                )

            # Number validation
            source_texts = [s.quote for s in sources]
            validated_report, unsupported = number_validator.validate(
                raw_answer, facts_block, metrics, source_texts
            )

            return CustomQueryResponse(
                prompt=clean_prompt,
                report=validated_report,
                sources=sources,
                unsupported_numbers=unsupported,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Custom query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


analysis_service = AnalysisService()
