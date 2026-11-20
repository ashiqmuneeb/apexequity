import re

from app.core.config import settings
from app.core.logger import logger
from app.schemas.analysis import SourceEvidenceNode
from app.services.metrics_service import metrics_service


EXPLANATION_PATTERN = re.compile(
    r"\b(why|how|explain|cause|driven|impact|risk|risks|threat|affect|effect|outlook|trend|strategy|breakdown|describe|discuss|compare|versus|vs)\b",
    re.IGNORECASE,
)

METRIC_PATTERNS = [
    ("operating_income", r"\b(operating\s+incomes?|operating\s+profits?|opinc)\b", "operating income"),
    ("net_income", r"\b(net\s+incomes?|net\s+profits?|bottom-?line)\b", "net income"),
    ("rd_expense", r"\b(research\s+and\s+development|r&d|r\s*&\s*d)\s*(expense|expenditure|cost|spending)?\b", "research and development (R&D) expense"),
    ("revenue", r"\b(revenues?|sales|top-?lines?|turnover)\b", "revenue"),
    ("gross_profit", r"\bgross\s+profits?\b", "gross profit"),
    ("cost_of_revenue", r"\b(cost\s+of\s+revenue|cost\s+of\s+goods\s+sold|cost\s+of\s+sales|cogs)\b", "cost of revenue"),
    ("gross_margin", r"\bgross\s+margins?\b", "gross margin"),
    ("growth_yoy", r"\b(revenue\s+growth|yoy\s+growth|growth\s+rate)\b", "YoY revenue growth"),
    ("cash_and_equiv", r"\b(cash\s+and\s+(?:cash\s+)?equivalents?|cash\s+balance|total\s+cash)\b", "cash and cash equivalents"),
    ("capex", r"\b(capital\s+expenditures?|capex|property[,\s]+plant\s+and\s+equipment)\b", "capital expenditure"),
]

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


class DeterministicLookupService:
    """Answers specific audited numeric financial inquiries directly from audited SEC XBRL facts

    with strict refusal guards (Condition 6).
    """

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

        # Guard 1: Questions asking why, how, or about risk/impact must go to RAG
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

        # Guard 3: Match exactly one financial metric
        matched_metrics = []
        for key, pat, label in METRIC_PATTERNS:
            if re.search(pat, clean_q, re.IGNORECASE):
                matched_metrics.append((key, label))

        if len(matched_metrics) != 1:
            # Either 0 metrics (uncovered/general) or multiple metrics -> fallback to RAG
            logger.debug(f"[DeterministicLookup] Matched {len(matched_metrics)} metrics -> dispatch to RAG")
            return None, [], False

        metric_key, metric_display = matched_metrics[0]

        # Guard 4: Year validation against available data
        metrics = metrics_service.get_metrics(clean_ticker)
        if not metrics or metrics.get("source") != "SEC filing":
            logger.debug(f"[DeterministicLookup] No audited SEC metrics for {clean_ticker} -> dispatch to RAG")
            return None, [], False

        current_fy = metrics.get("fiscal_year")
        prior_fy = metrics.get("prior_fiscal_year")
        company_name = metrics.get("company_name") or clean_ticker

        years_mentioned = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", clean_q)]
        if len(set(years_mentioned)) > 1:
            logger.debug("[DeterministicLookup] Multiple years in query -> dispatch to RAG")
            return None, [], False

        target_is_prior = False
        target_fy = current_fy

        if years_mentioned:
            req_year = years_mentioned[0]
            if req_year == current_fy:
                target_fy = current_fy
                target_is_prior = False
            elif prior_fy and req_year == prior_fy:
                target_fy = prior_fy
                target_is_prior = True
            else:
                # Requested year does NOT exist in company data (e.g. 2012, 1998, 2020)
                # Rule: Return EXACT refusal "Not disclosed in the retrieved filings." and NEVER substitute another year!
                logger.info(
                    f"[DeterministicLookup] Requested year {req_year} outside coverage ({current_fy}, {prior_fy}) -> EXACT REFUSAL"
                )
                return "Not disclosed in the retrieved filings.", [], True
        else:
            target_fy = current_fy

        # Extract value, tag, and accession for target period
        prefix = "prior_" if target_is_prior else ""
        raw_val = metrics.get(f"{prefix}{metric_key}_raw")
        val_label = metrics.get(f"{prefix}{metric_key}_label")
        tag_name = metrics.get(f"{metric_key}_tag") or metrics.get(f"{prefix}{metric_key}_tag") or "us-gaap"
        accn = (
            metrics.get(f"{prefix}{metric_key}_accession")
            or metrics.get(f"{prefix}accession_number")
            or metrics.get("accession_number")
            or "N/A"
        )

        if raw_val is None or val_label is None:
            logger.debug(f"[DeterministicLookup] Metric '{metric_key}' raw value missing for {clean_ticker} -> dispatch to RAG")
            return None, [], False

        # Format audited deterministic response
        report = (
            f"{company_name} reported {metric_display} of {val_label} "
            f"({raw_val:,.0f} USD) in fiscal year {target_fy}. [1]"
        )

        source_node = SourceEvidenceNode(
            ticker=clean_ticker,
            form="10-K",
            fiscal_year=target_fy,
            section="Item 8 (SEC EDGAR XBRL)",
            accession_number=accn,
            quote=f"Audited SEC EDGAR XBRL filing disclosure: {tag_name} = {val_label} ({raw_val:,.0f} USD) for fiscal year {target_fy} (Accession Number: {accn}).",
            rank=1,
            retrieval_score=1.0,
            rerank_score=1.0,
            score=1.0,
            text=f"Audited SEC EDGAR XBRL filing disclosure: {tag_name} = {val_label} ({raw_val:,.0f} USD) for fiscal year {target_fy} (Accession Number: {accn}).",
            metadata={
                "ticker": clean_ticker,
                "tag": tag_name,
                "fiscal_year": target_fy,
                "accession_number": accn,
                "method": "deterministic_xbrl_lookup",
            },
        )

        logger.info(
            f"[DeterministicLookup] Served audited {clean_ticker} {metric_key} ({val_label}) via deterministic path (Tag: {tag_name})"
        )
        return report, [source_node], False


deterministic_lookup_service = DeterministicLookupService()

