import re
from typing import Any

import numpy as np

from app.schemas.analysis import SourceEvidenceNode
from app.services.number_validator import number_validator


def normalize_text_for_eval(text: str) -> str:
    """Normalizes case, whitespace, curly vs straight quotes/apostrophes, dashes, and non-breaking spaces."""
    t = text.lower()
    t = re.sub(r"[\u2018\u2019\u201a\u201b\u2032]", "'", t)
    t = re.sub(r"[\u201c\u201d\u201e\u201f\u2033]", '"', t)
    t = re.sub(r"[\u2013\u2014]", "-", t)
    t = re.sub(r"[\u202f\u00a0]", " ", t)
    return " ".join(t.split())


def check_phrase_in_text(phrase: str, text: str, normalize: bool = True) -> bool:
    """Substring match with optional full normalization (case, whitespace, curly quotes, dashes)."""
    if normalize:
        return normalize_text_for_eval(phrase) in normalize_text_for_eval(text)
    norm_p = " ".join(phrase.lower().split())
    norm_t = " ".join(text.lower().split())
    return norm_p in norm_t


def check_numeric_match(
    report: str,
    expected_value: float,
    unit: str = "",
) -> tuple[bool, str]:
    """Evaluates whether the report contains a number matching the ground-truth XBRL value

    when rounded to the number of decimals used in the answer (Condition 2).
    Also supports scale conversions (e.g., $18,497 million matching $18.50 billion).
    """
    claims = number_validator.extract_claims(report)
    if not claims:
        return False, "No numeric claims found in report"

    for c in claims:
        val = c.value
        # Determine number of decimals in the claim text
        # e.g., "215.94" has 2 decimals; "215" has 0; "71.1%" has 1
        val_str = str(c.raw_text).replace(",", "").replace("$", "").replace("%", "").strip()
        parts = val_str.split(".")
        decimals = len(parts[1]) if len(parts) > 1 else 0

        # Scale comparison (Billions vs Millions vs exact)
        candidate_values = [val]
        # If expected is in Billions (e.g. 18.50) but report states 18497 (Millions)
        if expected_value < 1000 and val > 1000:
            candidate_values.append(val / 1000.0)
        # If expected is in Billions but report states in single units
        if expected_value < 1000 and val > 1e6:
            candidate_values.append(val / 1e9)

        for cv in candidate_values:
            # Round ground truth to the claim's decimal precision
            rounded_expected = round(expected_value, decimals)
            # Allow tolerance equal to rounding precision or 0.05
            tol = max(10 ** (-decimals) if decimals > 0 else 0.5, 0.05)
            if abs(cv - rounded_expected) <= tol or abs(cv - expected_value) <= tol:
                return True, f"Matched claim '{c.raw_text}' (val={cv}) with expected {expected_value}"

    return False, f"Expected {expected_value} {unit}, none of {[c.raw_text for c in claims]} matched within tolerance"


def evaluate_retrieval_hit(
    sources: list[SourceEvidenceNode],
    key_phrases: list[str],
    target_item: str | None = None,
    top_k: int = 5,
    normalize: bool = True,
) -> tuple[bool, bool, int | None, int | None]:
    """Computes retrieval hit status under two definitions (Condition 5):

    - def_a (Key Phrases Hit): A top_k chunk contains >= 2 of the key phrases (or all if < 2).
    - def_b (Strict Section Hit): def_a is satisfied AND the chunk section matches target_item.
    Returns: (hit_a, hit_b, rank_a, rank_b)
    """
    top_sources = sources[:top_k]
    min_phrases = min(2, len(key_phrases)) if len(key_phrases) >= 2 else 1

    hit_a = False
    hit_b = False
    rank_a = None
    rank_b = None

    for idx, src in enumerate(top_sources, 1):
        content = f"{src.quote} {src.text}"
        matches = [kp for kp in key_phrases if check_phrase_in_text(kp, content, normalize=normalize)]
        chunk_section = (src.section or "").strip().upper()
        target_norm = (target_item or "").strip().upper()

        if len(matches) >= min_phrases:
            if not hit_a:
                hit_a = True
                rank_a = idx

            # Strict section match
            section_matches = (
                not target_item
                or target_norm == chunk_section
                or target_norm in chunk_section
                or chunk_section in target_norm
            )
            if section_matches and not hit_b:
                hit_b = True
                rank_b = idx

    return hit_a, hit_b, rank_a, rank_b


def evaluate_chunk_retrieval_hit(
    sources: list[SourceEvidenceNode],
    gold_chunk_ids: list[str],
    top_k: int = 5,
) -> tuple[bool, int | None]:
    """Computes chunk-based retrieval hit status:

    Returns: (hit, rank) where hit is True if any top_k source node's chunk ID is in gold_chunk_ids.
    """
    top_sources = sources[:top_k]
    for idx, src in enumerate(top_sources, 1):
        cid = src.metadata.get("id")
        if cid and cid in gold_chunk_ids:
            return True, idx
    return False, None


def evaluate_citation_precision(
    report: str,
    sources: list[SourceEvidenceNode],
) -> tuple[float, int, int]:
    """Verifies whether cited chunks ([1], [2], ...) actually contain the number or key phrases

    claimed in the citation sentence.
    Returns: (precision, verified_citations, total_citations)
    """
    # Find all citation indices in the report
    citation_pattern = re.compile(r"\[(\d+)\]")
    citations = citation_pattern.findall(report)
    if not citations:
        return 1.0, 0, 0

    verified = 0
    total = len(citations)

    # Split report into sentences with their citations
    sentences = re.split(r"(?<=[.!?])\s+", report)

    for sent in sentences:
        c_matches = citation_pattern.findall(sent)
        if not c_matches:
            continue

        sent_claims = number_validator.extract_claims(sent)
        sent_words = set(re.findall(r"\b[A-Za-z0-9'-]{4,}\b", sent.lower())) - {
            "this", "that", "from", "with", "have", "were", "been", "reported", "fiscal"
        }

        for c_str in c_matches:
            c_idx = int(c_str) - 1
            if 0 <= c_idx < len(sources):
                src_text = f"{sources[c_idx].quote} {sources[c_idx].text}".lower()
                # Check if any number in the sentence appears in source text
                num_matched = False
                for claim in sent_claims:
                    # check if raw text or value is in source
                    val_str = str(int(claim.value)) if claim.value.is_integer() else f"{claim.value:.1f}"
                    if val_str in src_text or str(claim.raw_text).lower() in src_text:
                        num_matched = True
                        break

                # Or check significant word overlap
                src_words = set(re.findall(r"\b[A-Za-z0-9'-]{4,}\b", src_text))
                word_matched = len(sent_words.intersection(src_words)) >= 2

                if num_matched or word_matched or not sent_claims:
                    verified += 1

    precision = round(verified / total, 4) if total > 0 else 1.0
    return precision, verified, total


def compute_aggregate_metrics(eval_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregates benchmark metrics across categories: numeric, qualitative, and unanswerable."""
    total_items = len(eval_records)
    if total_items == 0:
        return {}

    # Category slices
    numeric_records = [r for r in eval_records if r["category"] == "numeric"]
    injected_num = [r for r in numeric_records if r.get("injected", False)]
    det_lookup_num = [r for r in numeric_records if r.get("path") == "deterministic"]
    not_injected_num = [
        r for r in numeric_records if not r.get("injected", False) and r.get("path") != "deterministic"
    ]
    qual_records = [r for r in eval_records if r["category"] == "qualitative"]
    unans_records = [r for r in eval_records if r["category"] == "unanswerable"]

    # 1. Retrieval Recall@5 & MRR (both raw and normalized per Condition 4)
    # Chunk-based retrieval (Condition 3 of Phase 4c)
    hits_chunk_5 = sum(1 for r in qual_records if r.get("chunk_hit_at_5", r.get("chunk_hit", False)))
    recall_chunk_5 = hits_chunk_5 / len(qual_records) if qual_records else 1.0
    hits_chunk_10 = sum(1 for r in qual_records if r.get("chunk_hit_at_10", r.get("chunk_hit", False)))
    recall_chunk_10 = hits_chunk_10 / len(qual_records) if qual_records else 1.0
    mrr_chunk = (
        np.mean([1.0 / r["chunk_rank"] if r.get("chunk_rank") else 0.0 for r in qual_records])
        if qual_records
        else 1.0
    )

    # Normalized (Condition 4 bug fix)
    hits_a_norm_5 = sum(1 for r in qual_records if r.get("hit_a_norm_5", r.get("hit_a_norm", r.get("hit_a", False))))
    recall_a_norm_5 = hits_a_norm_5 / len(qual_records) if qual_records else 1.0
    hits_a_norm_10 = sum(1 for r in qual_records if r.get("hit_a_norm_10", r.get("hit_a_norm", r.get("hit_a", False))))
    recall_a_norm_10 = hits_a_norm_10 / len(qual_records) if qual_records else 1.0
    mrr_a_norm = np.mean([1.0 / r["rank_a_norm"] if r.get("rank_a_norm") else (1.0 / r["rank_a"] if r.get("rank_a") else 0.0) for r in qual_records]) if qual_records else 1.0

    # Raw unnormalized
    hits_a_raw = sum(1 for r in qual_records if r.get("hit_a_raw", r.get("hit_a", False)))
    recall_a_raw = hits_a_raw / len(qual_records) if qual_records else 1.0
    mrr_a_raw = np.mean([1.0 / r["rank_a_raw"] if r.get("rank_a_raw") else (1.0 / r["rank_a"] if r.get("rank_a") else 0.0) for r in qual_records]) if qual_records else 1.0

    # Definition B (Strict section hit)
    hits_b = sum(1 for r in qual_records if r.get("hit_b", False))
    recall_b = hits_b / len(qual_records) if qual_records else 1.0
    mrr_b = np.mean([1.0 / r["rank_b"] if r.get("rank_b") else 0.0 for r in qual_records]) if qual_records else 1.0

    # 2. Numeric Accuracy (split into injected, deterministic lookup, and not injected per Condition 10)
    acc_overall_num = (
        sum(1 for r in numeric_records if r.get("numeric_correct", False)) / len(numeric_records)
        if numeric_records
        else 0.0
    )
    acc_injected = (
        sum(1 for r in injected_num if r.get("numeric_correct", False)) / len(injected_num)
        if injected_num
        else 0.0
    )
    acc_deterministic = (
        sum(1 for r in det_lookup_num if r.get("numeric_correct", False)) / len(det_lookup_num)
        if det_lookup_num
        else 0.0
    )
    acc_not_injected = (
        sum(1 for r in not_injected_num if r.get("numeric_correct", False)) / len(not_injected_num)
        if not_injected_num
        else 0.0
    )

    # 3. Citation Precision
    total_cit_verified = sum(r.get("citation_verified", 0) for r in eval_records)
    total_cit_count = sum(r.get("citation_total", 0) for r in eval_records)
    overall_cit_precision = (
        round(total_cit_verified / total_cit_count, 4) if total_cit_count > 0 else 1.0
    )

    # 4. Refusal Accuracy & False Refusal Rate (Condition 6)
    unans_correct = sum(1 for r in unans_records if r.get("refusal_correct", False))
    unans_by_model = sum(1 for r in unans_records if r.get("refusal_by") == "model")
    unans_by_404 = sum(1 for r in unans_records if r.get("refusal_by") == "404_api")
    refusal_accuracy = unans_correct / len(unans_records) if unans_records else 1.0

    # False refusal rate on answerable queries (numeric + qualitative)
    answerable = numeric_records + qual_records
    false_refusals = sum(1 for r in answerable if r.get("is_refusal", False))
    false_refusal_rate = false_refusals / len(answerable) if answerable else 0.0

    # 5. Unverified-Number Rate
    total_claims = sum(r.get("total_claims", 0) for r in eval_records)
    unverified_claims = sum(r.get("unverified_claims", 0) for r in eval_records)
    unverified_rate = (
        round(unverified_claims / total_claims, 4) if total_claims > 0 else 0.0
    )

    # 6. Latency Percentiles
    latencies = [r.get("latency_sec", 0.0) for r in eval_records if r.get("latency_sec") is not None]
    p50_lat = round(float(np.percentile(latencies, 50)), 3) if latencies else 0.0
    p95_lat = round(float(np.percentile(latencies, 95)), 3) if latencies else 0.0

    # 7. Faithfulness (LLM-judged)
    judged_records = [r for r in eval_records if r.get("judge_score") is not None]
    faithfulness_score = (
        round(float(np.mean([r["judge_score"] for r in judged_records])), 3)
        if judged_records
        else None
    )

    return {
        "dataset_size": total_items,
        "retrieval": {
            "chunk_recall_at_5": round(recall_chunk_5, 4),
            "chunk_recall_at_10": round(recall_chunk_10, 4),
            "chunk_mrr": round(float(mrr_chunk), 4),
            "recall_at_5_key_phrases": round(recall_a_norm_5, 4),
            "recall_at_10_key_phrases": round(recall_a_norm_10, 4),
            "mrr_key_phrases": round(float(mrr_a_norm), 4),
            "recall_at_5_raw": round(recall_a_raw, 4),
            "mrr_raw": round(float(mrr_a_raw), 4),
            "recall_at_5_strict_item": round(recall_b, 4),
            "mrr_strict_item": round(float(mrr_b), 4),
        },
        "numeric_accuracy": {
            "overall": round(acc_overall_num, 4),
            "injected_facts": round(acc_injected, 4),
            "deterministic_lookup": round(acc_deterministic, 4),
            "not_injected": round(acc_not_injected, 4),
        },
        "citation_precision": overall_cit_precision,
        "refusal": {
            "accuracy": round(refusal_accuracy, 4),
            "refusals_by_model": unans_by_model,
            "refusals_by_404_api": unans_by_404,
            "false_refusal_rate": round(false_refusal_rate, 4),
        },
        "grounding": {
            "total_number_claims": total_claims,
            "unverified_number_claims": unverified_claims,
            "unverified_number_rate": unverified_rate,
        },
        "latency_sec": {
            "p50": p50_lat,
            "p95": p95_lat,
        },
        "faithfulness": {
            "score": faithfulness_score,
            "evaluated_count": len(judged_records),
            "label": f"LLM-judged, n={len(judged_records)}" if judged_records else "Not evaluated",
        },
    }

