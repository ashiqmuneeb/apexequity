import re
from enum import Enum

from pydantic import BaseModel

from app.core.config import settings
from app.core.logger import logger
from app.schemas.analysis import SourceEvidenceNode
from app.services.metrics_service import metrics_service


# Condition 5(a): Only why, explain, cause, driven by, impact, risk.
# Do NOT treat "how much" or "how many" as explanation triggers.
EXPLANATION_PATTERN = re.compile(
    r"\b(why|explain|cause|driven\s+by|impact|risk|risks)\b",
    re.IGNORECASE,
)

# Aggregate indicators
RATIO_PATTERN = re.compile(
    r"\b(as\s+a\s+(?:percent|percentage)\s+of|ratio\s+of|per\s+share)\b",
    re.IGNORECASE,
)

GROWTH_PATTERN = re.compile(
    r"\b(?:year-over-year|yoy|annual)?\s*(?:net\s+sales|revenues?|sales)?\s*(?:growth|growth\s+rate)\b",
    re.IGNORECASE,
)

MARGIN_PATTERN = re.compile(
    r"\bgross\s+margins?(?:\s+percentage)?\b",
    re.IGNORECASE,
)

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


class AggregateType(str, Enum):
    AMOUNT = "amount"
    GROWTH_PERCENT = "growth_percent"
    MARGIN_PERCENT = "margin_percent"
    RATIO = "ratio"


class MetricIntent(BaseModel):
    metric_key: str
    aggregate_type: AggregateType
    display_name: str


class DeterministicLookupService:
    """Answers specific audited numeric financial inquiries directly from audited SEC XBRL facts

    with strict intent parsing, priority resolution, and refusal guards.
    """

    @classmethod
    def parse_intent(cls, query: str) -> MetricIntent | None:
        """Parses the financial inquiry into a structured MetricIntent object.

        Priority order:
        1. Ratio queries (e.g. 'as a percent of revenue') -> ratio aggregate type.
        2. Growth compound queries (e.g. 'year-over-year net sales growth') -> growth_yoy.
        3. Margin queries (e.g. 'gross margin percentage') -> gross_margin.
        4. Specific amount line-items -> amount aggregate type.
        """
        clean_q = query.strip()

        # Check for ratio patterns first
        if RATIO_PATTERN.search(clean_q):
            # Matches a derived ratio (e.g. R&D as a percent of revenue)
            return MetricIntent(
                metric_key="derived_ratio",
                aggregate_type=AggregateType.RATIO,
                display_name="derived ratio",
            )

        # Compound growth phrases beat single words ("net sales growth" is growth, not revenue)
        if GROWTH_PATTERN.search(clean_q):
            return MetricIntent(
                metric_key="growth_yoy",
                aggregate_type=AggregateType.GROWTH_PERCENT,
                display_name="year-over-year revenue growth",
            )

        # Margin queries
        if MARGIN_PATTERN.search(clean_q):
            return MetricIntent(
                metric_key="gross_margin",
                aggregate_type=AggregateType.MARGIN_PERCENT,
                display_name="gross margin",
            )

        # Specific amount metrics with word boundaries
        if re.search(r"\b(operating\s+incomes?|operating\s+profits?|opinc)\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="operating_income",
                aggregate_type=AggregateType.AMOUNT,
                display_name="operating income",
            )

        if re.search(r"\b(net\s+incomes?|net\s+profits?|bottom-?line)\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="net_income",
                aggregate_type=AggregateType.AMOUNT,
                display_name="net income",
            )

        if re.search(r"\b(research\s+and\s+development|r&d|r\s*&\s*d)\s*(expense|expenditure|cost|spending)?\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="rd_expense",
                aggregate_type=AggregateType.AMOUNT,
                display_name="research and development (R&D) expense",
            )

        if re.search(r"\b(gross\s+profits?)\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="gross_profit",
                aggregate_type=AggregateType.AMOUNT,
                display_name="gross profit",
            )

        if re.search(r"\b(cost\s+of\s+revenue|cost\s+of\s+goods\s+sold|cost\s+of\s+sales|cogs)\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="cost_of_revenue",
                aggregate_type=AggregateType.AMOUNT,
                display_name="cost of revenue",
            )

        if re.search(r"\b(cash\s+and\s+(?:cash\s+)?equivalents?|cash\s+balance|total\s+cash)\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="cash_and_equiv",
                aggregate_type=AggregateType.AMOUNT,
                display_name="cash and cash equivalents",
            )

        if re.search(r"\b(capital\s+expenditures?|capex|property[,\s]+plant\s+and\s+equipment)\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="capex",
                aggregate_type=AggregateType.AMOUNT,
                display_name="capital expenditure",
            )

        # Revenue matches single words only when growth/margin signals are absent
        if re.search(r"\b(revenues?|net\s+sales|sales|top-?lines?|turnover)\b", clean_q, re.IGNORECASE):
            return MetricIntent(
                metric_key="revenue",
                aggregate_type=AggregateType.AMOUNT,
                display_name="total revenue",
            )

        return None

    @classmethod
    def check_deterministic_lookup(
        cls,
        ticker: str,
        query: str,
    ) -> tuple[str | None, list[SourceEvidenceNode], bool]:
        """Evaluates whether query qualifies for deterministic XBRL fact dispatch.

        Returns: (report, sources, is_refusal) or (None, [], False) to fallback to RAG.
        """
        if not getattr(settings, "DETERMINISTIC_LOOKUP_ENABLED", True):
            return None, [], False

        clean_ticker = ticker.strip().upper()
        clean_q = query.strip()

        # Guard 1 (Condition 5a): Only why, explain, cause, driven by, impact, risk
        if EXPLANATION_PATTERN.search(clean_q):
            logger.debug(f"[DeterministicLookup] Query asks for explanation/risk -> dispatch to RAG: '{clean_q}'")
            return None, [], False

        # Guard 2: Questions mentioning multiple companies / compare must go to RAG
        other_tickers = [t for t in KNOWN_TICKERS if t != clean_ticker]
        for ot in other_tickers:
            if re.search(rf"\b{ot}\b", clean_q, re.IGNORECASE):
                logger.debug("[DeterministicLookup] Query references multiple tickers -> dispatch to RAG")
                return None, [], False
        for cname, ctick in COMPANY_TICKER_MAP.items():
            if ctick != clean_ticker and re.search(rf"\b{re.escape(cname)}\b", clean_q, re.IGNORECASE):
                logger.debug(f"[DeterministicLookup] Query references another company name '{cname}' -> dispatch to RAG")
                return None, [], False

        # Guard 3: Year presence and span validation (Condition 5b)
        years_mentioned = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", clean_q)]
        if not years_mentioned:
            # Missing year -> strictly fall back to RAG path
            logger.debug("[DeterministicLookup] Missing explicit fiscal year in query -> dispatch to RAG")
            return None, [], False

        if len(set(years_mentioned)) > 1:
            logger.debug("[DeterministicLookup] Multiple years in query -> dispatch to RAG")
            return None, [], False

        req_year = years_mentioned[0]

        metrics = metrics_service.get_metrics(clean_ticker)
        if not metrics or metrics.get("source") != "SEC filing":
            logger.debug(f"[DeterministicLookup] No audited SEC metrics for {clean_ticker} -> dispatch to RAG")
            return None, [], False

        current_fy = metrics.get("fiscal_year")
        if not current_fy:
            return None, [], False

        # Filing coverage span: SEC 10-K filings cover 3 fiscal years (current_fy - 2 to current_fy)
        min_span_year = current_fy - 2
        max_span_year = current_fy

        # Condition 5(b): Refuse ONLY when the year is entirely outside the span of ingested filings
        if req_year < min_span_year or req_year > max_span_year:
            logger.info(
                f"[DeterministicLookup] Year {req_year} outside filing span ({min_span_year}-{max_span_year}) -> EXACT REFUSAL"
            )
            return "Not disclosed in the retrieved filings.", [], True

        # Target year is inside the span of filings
        target_is_prior = (req_year == (current_fy - 1))
        target_fy = req_year

        # Guard 4: Parse intent into structured object
        intent = cls.parse_intent(clean_q)
        if intent is None:
            logger.debug(f"[DeterministicLookup] Could not parse metric intent from '{clean_q}' -> dispatch to RAG")
            return None, [], False

        # Condition 5(d): If query signals a different aggregate than the matched metric, fall back to RAG
        # Check for aggregate keywords
        diff_aggregate_words = re.findall(r"\b(growth|margin|percent|percentage|ratio|per\s+share)\b", clean_q, re.IGNORECASE)
        if intent.aggregate_type == AggregateType.AMOUNT and diff_aggregate_words:
            # Query mentions amount metric (e.g. revenue, rd_expense) but also aggregate words like percent/growth/margin
            logger.debug(
                f"[DeterministicLookup] Query signals different aggregate '{diff_aggregate_words}' than amount -> dispatch to RAG"
            )
            return None, [], False

        if intent.aggregate_type == AggregateType.RATIO:
            # Derived ratio not stored as a direct audited fact -> dispatch to RAG
            logger.debug(f"[DeterministicLookup] Query asks for ratio ({intent.display_name}) -> dispatch to RAG")
            return None, [], False

        # Guard 5: Value must exist in cached company facts for that metric and period (Condition 5b)
        metric_key = intent.metric_key
        prefix = "prior_" if target_is_prior else ""

        # Extract value, label, tag, period end date, accession
        company_name = metrics.get("company_name") or clean_ticker

        if metric_key == "growth_yoy":
            raw_val = metrics.get(f"{prefix}growth_yoy")
            val_label = metrics.get(f"{prefix}growth_label") or (f"+{raw_val}%" if raw_val is not None else None)
            tag_name = metrics.get(f"{prefix}growth_tag") or metrics.get("revenue_tag") or "Revenues"
            accn = metrics.get(f"{prefix}growth_accession") or metrics.get("accession_number") or "N/A"
            ped = metrics.get(f"{prefix}period_end_date") or metrics.get("period_end_date") or f"FY{target_fy}"
        elif metric_key == "gross_margin":
            raw_val = metrics.get(f"{prefix}gross_margin")
            val_label = metrics.get(f"{prefix}margin_label") or (f"{raw_val}%" if raw_val is not None else None)
            tag_name = metrics.get(f"{prefix}margin_tag") or "GrossProfit / Revenues"
            accn = metrics.get(f"{prefix}margin_accession") or metrics.get("accession_number") or "N/A"
            ped = metrics.get(f"{prefix}period_end_date") or metrics.get("period_end_date") or f"FY{target_fy}"
        else:
            raw_val = metrics.get(f"{prefix}{metric_key}_raw") or metrics.get(f"{prefix}{metric_key}")
            val_label = metrics.get(f"{prefix}{metric_key}_label")
            tag_name = (
                metrics.get(f"{prefix}{metric_key}_tag")
                or metrics.get(f"{metric_key}_tag")
                or "us-gaap"
            )
            accn = (
                metrics.get(f"{prefix}{metric_key}_accession")
                or metrics.get(f"{prefix}accession_number")
                or metrics.get("accession_number")
                or "N/A"
            )
            ped = metrics.get(f"{prefix}period_end_date") or metrics.get("period_end_date") or f"FY{target_fy}"

        # If inside filing span but value is not extracted for this year/metric -> fall back to RAG, NEVER refuse!
        if raw_val is None or val_label is None:
            logger.debug(
                f"[DeterministicLookup] Metric '{metric_key}' not extracted for {clean_ticker} FY{target_fy} -> fallback to RAG"
            )
            return None, [], False

        # Condition 5(c): Format audited deterministic response showing period end date, XBRL tag, accession number
        if intent.aggregate_type == AggregateType.GROWTH_PERCENT:
            report = (
                f"{company_name} reported year-over-year revenue growth of {val_label} "
                f"for the period ended {ped} (Tag: {tag_name}, Accession Number: {accn}) "
                f"in fiscal year {target_fy}. [1]"
            )
            quote = (
                f"Audited SEC EDGAR XBRL filing disclosure: {tag_name} = {val_label} "
                f"for the period ended {ped} (Accession Number: {accn}) in fiscal year {target_fy}."
            )
        elif intent.aggregate_type == AggregateType.MARGIN_PERCENT:
            report = (
                f"{company_name} reported gross margin of {val_label} "
                f"for the period ended {ped} (Tag: {tag_name}, Accession Number: {accn}) "
                f"in fiscal year {target_fy}. [1]"
            )
            quote = (
                f"Audited SEC EDGAR XBRL filing disclosure: {tag_name} = {val_label} "
                f"for the period ended {ped} (Accession Number: {accn}) in fiscal year {target_fy}."
            )
        else:
            report = (
                f"{company_name} reported {intent.display_name} of {val_label} "
                f"({raw_val:,.0f} USD) for the period ended {ped} "
                f"(Tag: {tag_name}, Accession Number: {accn}) in fiscal year {target_fy}. [1]"
            )
            quote = (
                f"Audited SEC EDGAR XBRL filing disclosure: {tag_name} = {val_label} ({raw_val:,.0f} USD) "
                f"for the period ended {ped} (Accession Number: {accn}) in fiscal year {target_fy}."
            )

        source_node = SourceEvidenceNode(
            ticker=clean_ticker,
            form="10-K",
            fiscal_year=target_fy,
            period_end=ped,
            section="Item 8 (SEC EDGAR XBRL)",
            accession_number=accn,
            quote=quote,
            rank=1,
            retrieval_score=1.0,
            rerank_score=1.0,
            score=1.0,
            text=quote,
            metadata={
                "ticker": clean_ticker,
                "tag": tag_name,
                "fiscal_year": target_fy,
                "period_end": ped,
                "accession_number": accn,
                "method": "deterministic_xbrl_lookup",
            },
        )

        logger.info(
            f"[DeterministicLookup] Served audited {clean_ticker} {metric_key} ({val_label}) via deterministic path (Tag: {tag_name})"
        )
        return report, [source_node], False


deterministic_lookup_service = DeterministicLookupService()
