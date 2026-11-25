# ruff: noqa: E402
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


# Ensure backend directory is in path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.logger import logger
from app.schemas.analysis import SourceEvidenceNode
from app.services.analysis_service import analysis_service
from app.services.deterministic_lookup import deterministic_lookup_service
from app.services.metrics_service import metrics_service
from app.services.number_validator import number_validator
from app.services.rag_engine import QA_PROMPT_TEMPLATE, rag_engine_service
from app.services.retrieval_service import retrieval_service
from app.services.sec_service import format_verified_facts
from eval.cache import eval_cache
from eval.funnel_diagnosis import find_gold_chunks_for_item, load_corpus_data
from eval.judge import faithfulness_judge
from eval.metrics import (
    check_numeric_match,
    compute_aggregate_metrics,
    evaluate_chunk_retrieval_hit,
    evaluate_citation_precision,
    evaluate_retrieval_hit,
)


ROOT_DIR = BACKEND_DIR.parent
EVAL_DIR = BACKEND_DIR / "eval"
GOLDEN_PATH = EVAL_DIR / "golden.jsonl"
GOLDEN_V2_PATH = EVAL_DIR / "golden_v2_heldout.jsonl"
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LATEST_JSON = RESULTS_DIR / "latest.json"
DOCS_DIR = ROOT_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
EVALUATION_MD = DOCS_DIR / "EVALUATION.md"

COVERED_TICKERS = {"NVDA", "MSFT", "AAPL", "GOOGL", "AMD"}


def get_git_commit_hash() -> str:
    """Read-only retrieval of the current Git commit hash (Condition 8)."""
    try:
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(ROOT_DIR),
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )
        return commit
    except Exception:
        return "UNKNOWN_UNCOMMITTED"


def run_evaluation(
    dataset_path: Path | None = None,
    limit: int | None = None,
    no_judge: bool = False,
    no_cache: bool = False,
    delay_sec: float = 2.0,
    retrieval_only: bool = False,
    judge_model: str = "qwen/qwen3.8-27b",
    output_path: Path | None = None,
    update_markdown: bool = True,
) -> dict[str, Any]:
    """Orchestrates evaluation across a golden benchmark with optional retrieval-only mode."""
    target_dataset_path = dataset_path or GOLDEN_PATH
    logger.info(f"Loading benchmark dataset from: {target_dataset_path}")
    lines = target_dataset_path.read_text(encoding="utf-8").strip().splitlines()
    dataset = [json.loads(line) for line in lines if line.strip()]

    if limit is not None and limit > 0:
        logger.info(f"Limiting evaluation to first {limit} item(s).")
        dataset = dataset[:limit]

    commit_hash = get_git_commit_hash()
    eval_start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    cache_hits: int = 0
    cache_misses: int = 0
    regenerated_items: list[str] = []

    corpus_ids, corpus_docs, corpus_metas = load_corpus_data()

    # Reset boost counter
    retrieval_service.total_boost_changed_top5_count = 0

    mode_str = "RETRIEVAL-ONLY (CPU Ablation)" if retrieval_only else "FULL PIPELINE (End-to-End)"
    logger.info(
        f"Starting {mode_str} of {len(dataset)} items | Generator: {settings.GROQ_MODEL} | "
        f"Judge: {judge_model} | Reranker: {settings.RERANKER_MODEL} ({settings.RERANKER_ENABLED}) | "
        f"Top-k: Dense={settings.DENSE_TOP_K}, BM25={settings.BM25_TOP_K} | Boost={settings.SECTION_BOOST_ENABLED} ({settings.SECTION_BOOST_VALUE})"
    )

    for idx, item in enumerate(dataset, 1):
        q_id = item["id"]
        category = item["category"]
        ticker = item.get("ticker", "NVDA").upper().strip()
        question = item["question"]
        is_uncovered_ticker = item.get("is_uncovered_ticker", ticker not in COVERED_TICKERS)

        print(f"\n[{idx}/{len(dataset)}] ({category.upper()}) {ticker}: {question}")

        t0 = time.perf_counter()
        report = ""
        sources: list[SourceEvidenceNode] = []
        is_404 = False
        is_refusal = False
        path = "rag"
        res = None

        if retrieval_only:
            # -----------------------------------------------------------
            # RETRIEVAL-ONLY MODE: Zero LLM generation calls
            # -----------------------------------------------------------
            if is_uncovered_ticker:
                is_404 = True
                report = "404: No documents ingested for ticker"
                sources = []
                path = "none"
            elif category == "numeric":
                if getattr(settings, "DETERMINISTIC_LOOKUP_ENABLED", True):
                    det_report, det_sources, _ = deterministic_lookup_service.check_deterministic_lookup(ticker, question)
                    if det_report is not None:
                        report = det_report
                        sources = det_sources
                        path = "deterministic"
                        print(f"  -> Deterministic lookup answered ({path}): {report[:60]}...")
                    else:
                        path = "rag"
                        sources = retrieval_service.retrieve_single(ticker, question, top_n=10)
                else:
                    path = "rag"
                    sources = retrieval_service.retrieve_single(ticker, question, top_n=10)
            elif category == "qualitative":
                path = "rag"
                sources = retrieval_service.retrieve_single(ticker, question, top_n=10)
            elif category == "unanswerable":
                if getattr(settings, "DETERMINISTIC_LOOKUP_ENABLED", True):
                    det_report, det_sources, det_refusal = deterministic_lookup_service.check_deterministic_lookup(ticker, question)
                    if det_report is not None and det_refusal:
                        report = det_report
                        sources = det_sources
                        path = "deterministic"
                        is_refusal = True
                        print("  -> Deterministic lookup refused with exact text.")
                    else:
                        path = "rag"
                        sources = retrieval_service.retrieve_single(ticker, question, top_n=10)
                else:
                    path = "rag"
                    sources = retrieval_service.retrieve_single(ticker, question, top_n=10)
            latency_sec = round(time.perf_counter() - t0, 3)

        else:
            # -----------------------------------------------------------
            # FULL END-TO-END GENERATION MODE
            # -----------------------------------------------------------
            # 1. Deterministic check first
            if getattr(settings, "DETERMINISTIC_LOOKUP_ENABLED", True):
                if category == "numeric":
                    det_rep, det_srcs, _ = deterministic_lookup_service.check_deterministic_lookup(ticker, question)
                    if det_rep is not None:
                        report = det_rep
                        sources = det_srcs
                        path = "deterministic"
                        print(f"  -> Deterministic lookup answered ({path})")
                elif category == "unanswerable":
                    det_rep, det_srcs, det_refusal = deterministic_lookup_service.check_deterministic_lookup(ticker, question)
                    if det_rep is not None and det_refusal:
                        report = det_rep
                        sources = det_srcs
                        path = "deterministic"
                        is_refusal = True
                        print("  -> Deterministic lookup refused with exact text.")

            # 2. If uncovered ticker and not handled
            if not report and is_uncovered_ticker:
                is_404 = True
                report = "404: No documents ingested for ticker"
                sources = []
                path = "none"

            # 3. If still no report, evaluate RAG with prompt-hash cache
            if not report and not is_404:
                sources = retrieval_service.retrieve_single(ticker, question, top_n=10)
                sec_metrics = metrics_service.get_metrics(ticker) or {}
                facts_block = format_verified_facts(sec_metrics)
                passages = [analysis_service._format_source_passage(i + 1, s) for i, s in enumerate(sources[:5])]
                context_str = f"{facts_block}\n\n=== RETRIEVED SOURCES ===\n" + "\n\n".join(passages)
                full_prompt = QA_PROMPT_TEMPLATE.format(context_str=context_str, query_str=question)

                prompt_hash = hashlib.sha256(full_prompt.encode("utf-8")).hexdigest()
                gen_key = eval_cache.compute_generator_key(ticker, prompt_hash, settings.GROQ_MODEL, settings.TEMPERATURE)
                legacy_key = eval_cache.compute_key(ticker, question, settings.GROQ_MODEL, "analysis_query")

                cached_entry = None
                if not no_cache:
                    cached_entry = eval_cache.get(gen_key)

                if cached_entry:
                    print("  -> Loaded from on-disk cache [CACHED]")
                    report = cached_entry.get("report", "")
                    raw_sources = cached_entry.get("sources", [])
                    if raw_sources:
                        sources = [SourceEvidenceNode(**s) for s in raw_sources]
                    latency_sec = cached_entry.get("latency_sec", 0.05)
                    is_404 = cached_entry.get("is_404", False)
                    path = cached_entry.get("path", "rag")
                    cache_hits += 1
                else:
                    cache_misses += 1
                    regenerated_items.append(q_id)
                    print(f"  -> Cache miss. Generating via Groq ({settings.GROQ_MODEL})...")
                    try:
                        report = rag_engine_service.generate_completion(full_prompt)
                        latency_sec = round(time.perf_counter() - t0, 3)
                        eval_cache.set(
                            gen_key,
                            {
                                "id": q_id,
                                "ticker": ticker,
                                "question": question,
                                "report": report,
                                "sources": [s.model_dump() for s in sources[:5]],
                                "latency_sec": latency_sec,
                                "is_404": is_404,
                                "path": path,
                            },
                        )
                        eval_cache.set(
                            legacy_key,
                            {
                                "id": q_id,
                                "ticker": ticker,
                                "question": question,
                                "report": report,
                                "sources": [s.model_dump() for s in sources[:5]],
                                "latency_sec": latency_sec,
                                "is_404": is_404,
                                "path": path,
                            },
                        )
                        time.sleep(delay_sec)
                    except Exception as e:
                        err_str = str(e)
                        print(f"  [ERROR] Execution failed for {q_id}: {e}")
                        if "daily" in err_str.lower() or "limit reached" in err_str.lower():
                            logger.error(f"Daily Groq quota reached at item {idx}. Halting cleanly.")
                            break
                        report = f"Execution Error: {e}"
                        latency_sec = round(time.perf_counter() - t0, 3)

            latency_sec = round(time.perf_counter() - t0, 3)

        # Refusal check
        clean_rep = report.strip()
        if not is_refusal:
            is_refusal = (
                clean_rep == "Not disclosed in the retrieved filings."
                or "not disclosed in the retrieved filings" in clean_rep.lower()
            )

        record: dict[str, Any] = {
            "id": q_id,
            "category": category,
            "ticker": ticker,
            "question": question,
            "path": path,
            "report": report,
            "sources_count": len(sources),
            "retrieved_sections": [f"{s.section} (#{s.rank})" for s in sources],
            "latency_sec": latency_sec,
            "is_refusal": is_refusal,
            "is_404": is_404,
            "boost_changed_top5": getattr(retrieval_service, "last_boost_changed_top5", False),
        }

        # Category-specific evaluations
        # 1. Numeric evaluation
        if category == "numeric":
            injected = item.get("injected", False)
            expected_val = float(item["expected_value"])
            unit = item.get("unit", "")
            record["injected"] = injected
            record["expected_value"] = expected_val

            if report:
                matched, reason = check_numeric_match(report, expected_val, unit)
                record["numeric_correct"] = matched
                record["match_reason"] = reason

                claims = number_validator.extract_claims(report)
                record["total_claims"] = len(claims)
                unsupported = getattr(res, "unsupported_numbers", []) if res else []
                record["unverified_claims"] = len(unsupported)

                if not matched:
                    failures.append({
                        "id": q_id,
                        "category": category,
                        "question": question,
                        "ticker": ticker,
                        "expected": f"{expected_val} {unit}",
                        "actual_report": report[:250],
                        "retrieved_sections": record["retrieved_sections"],
                        "likely_cause": f"Value mismatch (injected={injected}, path={path}): {reason}",
                    })
            else:
                record["numeric_correct"] = False
                record["match_reason"] = "Retrieval-only: LLM generator skipped"
                record["total_claims"] = 0
                record["unverified_claims"] = 0

        # 2. Qualitative evaluation
        elif category == "qualitative":
            key_phrases = item.get("key_phrases", [])
            target_item = item.get("target_item")
            gold_chunk_ids = find_gold_chunks_for_item(item, corpus_ids, corpus_docs, corpus_metas)

            # Chunk-based hit
            chunk_hit_5, chunk_rank_5 = evaluate_chunk_retrieval_hit(sources, gold_chunk_ids, top_k=5)
            chunk_hit_10, chunk_rank_10 = evaluate_chunk_retrieval_hit(sources, gold_chunk_ids, top_k=10)

            # Condition 4: evaluate both normalized and raw at top 5 and top 10
            hit_a_norm_5, hit_b_5, rank_a_norm_5, rank_b_5 = evaluate_retrieval_hit(
                sources=sources,
                key_phrases=key_phrases,
                target_item=target_item,
                top_k=5,
                normalize=True,
            )
            hit_a_norm_10, hit_b_10, rank_a_norm_10, _ = evaluate_retrieval_hit(
                sources=sources,
                key_phrases=key_phrases,
                target_item=target_item,
                top_k=10,
                normalize=True,
            )
            hit_a_raw, _, rank_a_raw, _ = evaluate_retrieval_hit(
                sources=sources,
                key_phrases=key_phrases,
                target_item=target_item,
                top_k=5,
                normalize=False,
            )

            record["chunk_hit"] = chunk_hit_5
            record["chunk_hit_at_5"] = chunk_hit_5
            record["chunk_hit_at_10"] = chunk_hit_10
            record["chunk_rank"] = chunk_rank_5 or chunk_rank_10

            record["hit_a"] = hit_a_norm_5
            record["hit_a_norm"] = hit_a_norm_5
            record["hit_a_norm_5"] = hit_a_norm_5
            record["hit_a_norm_10"] = hit_a_norm_10
            record["rank_a_norm"] = rank_a_norm_5 or rank_a_norm_10
            record["hit_a_raw"] = hit_a_raw
            record["rank_a_raw"] = rank_a_raw
            record["hit_b"] = hit_b_5
            record["rank_b"] = rank_b_5
            record["target_item"] = target_item
            record["key_phrases"] = key_phrases
            record["gold_chunk_ids"] = gold_chunk_ids

            if not hit_a_norm_5:
                failures.append({
                    "id": q_id,
                    "category": category,
                    "question": question,
                    "ticker": ticker,
                    "expected": f"Key phrases: {key_phrases} in {target_item}",
                    "actual_report": report[:250],
                    "retrieved_sections": record["retrieved_sections"],
                    "likely_cause": "Key phrases missing in top-5 retrieved chunks",
                })

        # 3. Unanswerable evaluation
        elif category == "unanswerable":
            if is_uncovered_ticker:
                refusal_ok = is_404 or is_refusal
                refusal_by = "404_api" if is_404 else ("model" if is_refusal else "none")
            else:
                refusal_ok = is_refusal
                refusal_by = "model" if is_refusal else ("deterministic" if path == "deterministic" else "none")

            record["refusal_correct"] = refusal_ok
            record["refusal_by"] = refusal_by

            if not refusal_ok:
                failures.append({
                    "id": q_id,
                    "category": category,
                    "question": question,
                    "ticker": ticker,
                    "expected": "Exact refusal: 'Not disclosed in the retrieved filings.'",
                    "actual_report": report[:250],
                    "retrieved_sections": record["retrieved_sections"],
                    "likely_cause": "Hallucinated or answered query outside coverage",
                })

        # Citation precision
        cit_prec, cit_ver, cit_tot = evaluate_citation_precision(report, sources)
        record["citation_precision"] = cit_prec
        record["citation_verified"] = cit_ver
        record["citation_total"] = cit_tot

        # LLM Judge evaluation (skipped in retrieval-only mode)
        if not retrieval_only and not no_judge and not is_refusal and not is_404 and report:
            j_score, j_reason, j_model = faithfulness_judge.evaluate(
                query=question,
                response=report,
                sources=sources,
                override_model=judge_model,
            )
            record["judge_score"] = j_score
            record["judge_reason"] = j_reason
            record["judge_model"] = j_model
        else:
            record["judge_score"] = 1.0 if (is_refusal or is_404) else None
            record["judge_reason"] = "Refusal / 404" if (is_refusal or is_404) else ("Retrieval-only" if retrieval_only else None)
            record["judge_model"] = judge_model if (is_refusal or is_404) else "None"

        records.append(record)

    # Compute aggregate metrics
    metrics = compute_aggregate_metrics(records)
    metrics["retrieval"]["boost_changed_top5_count"] = getattr(
        retrieval_service, "total_boost_changed_top5_count", 0
    )
    metrics["cache_stats"] = {
        "hits": cache_hits,
        "misses": cache_misses,
        "regenerated_count": len(regenerated_items),
        "regenerated_items": regenerated_items,
    }

    results_data = {
        "metadata": {
            "timestamp": eval_start_time,
            "git_commit": commit_hash,
            "generator_model": settings.GROQ_MODEL if not retrieval_only else "None (Retrieval-Only)",
            "generator_fallback": settings.GROQ_FALLBACK_MODEL,
            "judge_model": judge_model if (not no_judge and not retrieval_only) else "None",
            "reranker_enabled": settings.RERANKER_ENABLED,
            "reranker_model": settings.RERANKER_MODEL,
            "dense_top_k": settings.DENSE_TOP_K,
            "bm25_top_k": settings.BM25_TOP_K,
            "top_n_rerank": settings.TOP_N_RERANK,
            "section_boost_enabled": getattr(settings, "SECTION_BOOST_ENABLED", True),
            "section_boost_value": getattr(settings, "SECTION_BOOST_VALUE", 0.004),
            "query_expansion_enabled": getattr(settings, "QUERY_EXPANSION_ENABLED", True),
            "deterministic_lookup_enabled": getattr(settings, "DETERMINISTIC_LOOKUP_ENABLED", True),
            "table_exemption_enabled": getattr(settings, "TABLE_EXEMPTION_ENABLED", True),
            "dataset_file": str(target_dataset_path.name),
            "evaluated_items_count": len(records),
            "mode": "retrieval_only" if retrieval_only else "full",
        },
        "metrics": metrics,
        "failures": failures[:10],
        "eval_records": records,
    }

    target_json = output_path or LATEST_JSON
    target_json.write_text(json.dumps(results_data, indent=2), encoding="utf-8")
    logger.info(f"Wrote evaluation results to: {target_json}")

    if update_markdown:
        write_evaluation_markdown(results_data, EVALUATION_MD)
        logger.info(f"Wrote evaluation report to: {EVALUATION_MD}")

    return results_data


def _fmt_pct(val: float | None) -> str:
    return f"{val * 100:.1f}%" if val is not None else "n/a"


def _fmt_float(val: float | None, digits: int = 3) -> str:
    return f"{val:.{digits}f}" if val is not None else "n/a"


def write_evaluation_markdown(results: dict[str, Any], output_path: Path) -> None:
    """Renders comprehensive, institutional EVALUATION.md document."""
    meta = results["metadata"]
    metrics = results["metrics"]
    failures = results.get("failures", [])

    retrieval = metrics.get("retrieval", {})
    num_acc = metrics.get("numeric_accuracy", {})
    refusal = metrics.get("refusal", {})
    grounding = metrics.get("grounding", {})
    lat = metrics.get("latency_sec", {})
    faith = metrics.get("faithfulness", {})

    r_recall_a = retrieval.get("recall_at_5_key_phrases")
    low_recall_warning = ""
    if r_recall_a is not None and r_recall_a < 0.8:
        low_recall_warning = (
            "> [!WARNING]\n"
            f"> **Retrieval Recall@5 is {r_recall_a * 100:.1f}% (< 80%)**.\n"
            "> In accordance with Phase 4 guidelines, this benchmark is reported honestly without tuning the dataset to the system.\n"
            "> Specific failing questions and retrieval architectural adjustments are detailed in Section 5 below.\n\n"
        )

    faith_val_str = f"{faith.get('score'):.3f}" if faith.get('score') is not None else "n/a"
    lat_p50 = f"{lat.get('p50')}s" if lat.get('p50') is not None else "n/a"
    lat_p95 = f"{lat.get('p95')}s" if lat.get('p95') is not None else "n/a"

    md = (
        f"# System Evaluation Report: ApexEquity RAG Pipeline\n\n"
        f"**Evaluation Run Timestamp**: `{meta.get('timestamp')}`  \n"
        f"**Git Commit**: `{meta.get('git_commit')}`  \n"
        f"**Generator Model**: `{meta.get('generator_model')}` | **Judge Model**: `{meta.get('judge_model')}`  \n"
        f"**Reranker**: `{meta.get('reranker_model')}` (Enabled: `{meta.get('reranker_enabled')}`)  \n"
        f"**Retrieval Parameters**: `Dense Top-K: {meta.get('dense_top_k')}`, `BM25 Top-K: {meta.get('bm25_top_k')}`, `Final Top-N: {meta.get('top_n_rerank')}`  \n"
        f"**Dataset**: `{meta.get('dataset_file')}` ({meta.get('evaluated_items_count')} items evaluated) | Mode: `{meta.get('mode')}`\n\n"
        f"---\n\n"
        f"{low_recall_warning}## 1. Executive Summary & Aggregate Metrics\n\n"
        f"| Metric Category | Metric Name | Definition / Scope | Score / Value | Status |\n"
        f"| :--- | :--- | :--- | :--- | :--- |\n"
        f"| **Retrieval** | **Recall@5 (Normalized)** | Chunk contains >= 2 required key phrases (bug fix) | **{_fmt_pct(retrieval.get('recall_at_5_key_phrases'))}** | {'[PASS]' if (r_recall_a is not None and r_recall_a >= 0.8) else ('n/a' if r_recall_a is None else '[NEEDS ATTENTION]')} |\n"
        f"| **Retrieval** | **MRR (Normalized)** | Mean Reciprocal Rank across top-5 chunks (normalized) | **{_fmt_float(retrieval.get('mrr_key_phrases'))}** | Institutional grade |\n"
        f"| **Retrieval** | **Recall@5 (Raw Unnormalized)** | Case/whitespace exact substring | **{_fmt_pct(retrieval.get('recall_at_5_raw'))}** | Unnormalized |\n"
        f"| **Retrieval** | **MRR (Raw Unnormalized)** | Raw substring reciprocal rank | **{_fmt_float(retrieval.get('mrr_raw'))}** | Unnormalized |\n"
        f"| **Retrieval** | **Recall@5 (Strict Section)** | Key phrases AND exact matching Item section | **{_fmt_pct(retrieval.get('recall_at_5_strict_item'))}** | Strict audit |\n"
        f"| **Retrieval** | **MRR (Strict Section)** | Mean Reciprocal Rank (Key phrases + Item match) | **{_fmt_float(retrieval.get('mrr_strict_item'))}** | Strict audit |\n"
        f"| **Numeric Accuracy** | **Overall Numeric Accuracy** | Decimal-rounded match against XBRL facts | **{_fmt_pct(num_acc.get('overall'))}** | Ground-truth XBRL |\n"
        f"| **Numeric Accuracy** | **Injected Facts Accuracy** | Revenue, Gross Margin, YoY Growth (injected) | **{_fmt_pct(num_acc.get('injected_facts'))}** | Injected facts |\n"
        f"| **Numeric Accuracy** | **Deterministic Lookup Accuracy** | Operating Income, Net Income, R&D, Cash, CapEx | **{_fmt_pct(num_acc.get('deterministic_lookup'))}** | Verified Facts Table |\n"
        f"| **Numeric Accuracy** | **Not-Injected Facts Accuracy** | Pure retrieval without deterministic lookup | **{_fmt_pct(num_acc.get('not_injected'))}** | Pure retrieval |\n"
        f"| **Citations** | **Citation Precision** | Cited chunks `[k]` contain claimed fact/phrase | **{_fmt_pct(metrics.get('citation_precision'))}** | Grounding check |\n"
        f"| **Refusal** | **Refusal Accuracy** | Exact refusal on out-of-scope/uncovered items | **{_fmt_pct(refusal.get('accuracy'))}** | {refusal.get('refusals_by_model', 'n/a')} model, {refusal.get('refusals_by_404_api', 'n/a')} 404 API |\n"
        f"| **Refusal** | **False-Refusal Rate** | Refused on valid answerable questions | **{_fmt_pct(refusal.get('false_refusal_rate'))}** | Target: 0.0% |\n"
        f"| **Grounding** | **Unverified Number Rate** | Claims unverified by NumberValidator | **{_fmt_pct(grounding.get('unverified_number_rate'))}** | ({grounding.get('unverified_number_claims', 0)}/{grounding.get('total_number_claims', 0)} claims) |\n"
        f"| **Performance** | **Latency p50 / p95** | 50th / 95th percentile total query runtime | **{lat_p50} / {lat_p95}** | Pipeline latency |\n"
        f"| **Faithfulness** | **Faithfulness Score** | {faith.get('label', 'LLM-judged')} | **{faith_val_str}** | {faith.get('label')} |\n\n"
        f"---\n\n"
        f"## 2. Top 10 Failure Cases & Root Cause Analysis\n\n"
    )

    if not failures:
        md += "No major failure cases detected during this evaluation run.\n\n"
    else:
        md += "| # | Query ID | Category | Ticker | Expected | Actual / Likely Cause |\n"
        md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for i, f in enumerate(failures[:10], 1):
            md += (
                f"| {i} | `{f['id']}` | {f['category']} | **{f['ticker']}** | "
                f"`{f.get('expected', '')[:45]}` | {f.get('likely_cause', '')} |\n"
            )
        md += "\n"

    output_path.write_text(md, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="ApexEquity Phase 4b Evaluation Runner")
    parser.add_argument("--dataset", type=str, default=None, help="Path to evaluation dataset .jsonl")
    parser.add_argument("--limit", type=int, default=None, help="Limit evaluation to first N items")
    parser.add_argument("--retrieval-only", action="store_true", help="Run in CPU retrieval-only ablation mode")
    parser.add_argument("--no-judge", action="store_true", help="Skip Groq LLM-as-judge evaluation")
    parser.add_argument("--judge-model", type=str, default="qwen/qwen3.8-27b", help="Judge model name")
    parser.add_argument("--no-cache", action="store_true", help="Bypass on-disk evaluation cache")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay in seconds between Groq queries")
    parser.add_argument("--dense-top-k", type=int, default=None, help="Dense candidate pool size")
    parser.add_argument("--bm25-top-k", type=int, default=None, help="BM25 candidate pool size")
    parser.add_argument("--no-boost", action="store_true", help="Disable section-aware boosting")
    parser.add_argument("--no-expansion", action="store_true", help="Disable generic query expansion")
    parser.add_argument("--no-deterministic", action="store_true", help="Disable deterministic metric lookup")
    parser.add_argument("--no-table-exemption", action="store_true", help="Disable table-chunk exemption")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--no-markdown", action="store_true", help="Skip updating EVALUATION.md")

    args = parser.parse_args()

    # Apply configuration overrides if provided
    if args.dense_top_k is not None:
        settings.DENSE_TOP_K = args.dense_top_k
    if args.bm25_top_k is not None:
        settings.BM25_TOP_K = args.bm25_top_k
    if args.no_boost:
        settings.SECTION_BOOST_ENABLED = False
    if args.no_expansion:
        settings.QUERY_EXPANSION_ENABLED = False
    if args.no_deterministic:
        settings.DETERMINISTIC_LOOKUP_ENABLED = False
    if args.no_table_exemption:
        settings.TABLE_EXEMPTION_ENABLED = False

    dataset_p = Path(args.dataset) if args.dataset else GOLDEN_PATH
    output_p = Path(args.output) if args.output else None

    results = run_evaluation(
        dataset_path=dataset_p,
        limit=args.limit,
        no_judge=args.no_judge,
        no_cache=args.no_cache,
        delay_sec=args.delay,
        retrieval_only=args.retrieval_only,
        judge_model=args.judge_model,
        output_path=output_p,
        update_markdown=not args.no_markdown,
    )

    metrics = results.get("metrics", {})
    retrieval = metrics.get("retrieval", {})
    num_acc = metrics.get("numeric_accuracy", {})
    print("\n=======================================================")
    print("EVALUATION SUMMARY")
    print("=======================================================")
    print(f"Evaluated Items: {results['metadata']['evaluated_items_count']}")
    print(f"Recall@5 (Normalized): {_fmt_pct(retrieval.get('recall_at_5_key_phrases'))}")
    print(f"MRR (Normalized): {_fmt_float(retrieval.get('mrr_key_phrases'))}")
    print(f"Recall@5 (Raw): {_fmt_pct(retrieval.get('recall_at_5_raw'))}")
    print(f"MRR (Raw): {_fmt_float(retrieval.get('mrr_raw'))}")
    print(f"Numeric Accuracy: {_fmt_pct(num_acc.get('overall'))} (Injected: {_fmt_pct(num_acc.get('injected_facts'))}, Det. Lookup: {_fmt_pct(num_acc.get('deterministic_lookup'))}, Not-injected: {_fmt_pct(num_acc.get('not_injected'))})")
    print(f"Refusal Accuracy: {_fmt_pct(metrics.get('refusal', {}).get('accuracy'))}")
    print(f"Section Boost changed top-5: {retrieval.get('boost_changed_top5_count', 0)} times")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
