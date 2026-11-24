# ruff: noqa: E402
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from eval.metrics import compute_aggregate_metrics
from eval.run import run_evaluation


EVAL_DIR = BACKEND_DIR / "eval"
GOLDEN_V1 = EVAL_DIR / "golden.jsonl"
GOLDEN_V2 = EVAL_DIR / "golden_v2_heldout.jsonl"
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_table_a_retrieval():
    print("\n==================================================================")
    print("TASK 1 - TABLE A: RETRIEVAL-ONLY EVALUATION ACROSS CONFIGURATIONS")
    print("==================================================================")

    configs = [
        ("1. Bug Fix (10+10, text=full_text)", GOLDEN_V1, 10, 10, False, False, False, False, "ablation_v1_bugfix.json"),
        ("2. Table Exemption Only", GOLDEN_V1, 10, 10, False, False, False, True, "ablation_v1_table_exemption.json"),
        ("3. Candidate Pool 20+20", GOLDEN_V1, 20, 20, False, False, False, False, "ablation_v1_pool20.json"),
        ("4. Query Expansion", GOLDEN_V1, 10, 10, False, True, False, False, "ablation_v1_query_expansion.json"),
        ("5. Section Boost", GOLDEN_V1, 10, 10, True, False, False, False, "ablation_v1_section_boost.json"),
        ("6. Deterministic Lookup (Retrieval Path Untouched)", GOLDEN_V1, 10, 10, False, False, True, False, "ablation_v1_det_lookup.json"),
        ("7. All Improvements on v1 (Default Rules Applied)", GOLDEN_V1, 10, 10, False, False, True, False, "v1_all_improvements_retrieval.json"),
        ("8. Baseline on Held-Out v2", GOLDEN_V2, 10, 10, False, False, False, False, "v2_heldout_baseline_retrieval.json"),
        ("9. All Improvements on Held-Out v2", GOLDEN_V2, 10, 10, False, False, True, False, "v2_heldout_all_improvements_retrieval.json"),
    ]

    table_a_results = []

    for name, dpath, dk, bk, sb, qe, dl, te, fname in configs:
        settings.DENSE_TOP_K = dk
        settings.BM25_TOP_K = bk
        settings.SECTION_BOOST_ENABLED = sb
        settings.QUERY_EXPANSION_ENABLED = qe
        settings.DETERMINISTIC_LOOKUP_ENABLED = dl
        settings.TABLE_EXEMPTION_ENABLED = te

        out_path = RESULTS_DIR / fname
        if out_path.exists():
            data = json.loads(out_path.read_text(encoding="utf-8"))
            m = compute_aggregate_metrics(data["eval_records"])
            res = {"metrics": m, "eval_records": data["eval_records"]}
        else:
            res = run_evaluation(
                dataset_path=dpath,
                retrieval_only=True,
                output_path=out_path,
                update_markdown=False,
            )

        r_metrics = res["metrics"]["retrieval"]
        lat = res["metrics"].get("latency_sec", {})

        table_a_results.append({
            "config": name,
            "dataset": "v1 (n=18)" if "v1" in str(dpath) else "v2 (n=10)",
            "chunk_recall_5": r_metrics.get("chunk_recall_at_5", 0.0),
            "chunk_recall_10": r_metrics.get("chunk_recall_at_10", 0.0),
            "chunk_mrr": r_metrics.get("chunk_mrr", 0.0),
            "kp_recall_5": r_metrics.get("recall_at_5_key_phrases", 0.0),
            "kp_recall_10": r_metrics.get("recall_at_10_key_phrases", 0.0),
            "kp_mrr": r_metrics.get("mrr_key_phrases", 0.0),
            "lat_p50": lat.get("p50", 0.0),
            "lat_p95": lat.get("p95", 0.0),
        })

    print("\n--- TABLE A RESULTS SUMMARY ---")
    print(f"{'Configuration':<45} | {'Data':<9} | {'Chunk R@5':<10} | {'Chunk R@10':<11} | {'Chunk MRR':<10} | {'KP R@5':<8} | {'KP R@10':<9} | {'KP MRR':<7} | {'Latency p50/p95'}")
    print("-" * 145)
    for row in table_a_results:
        print(
            f"{row['config']:<45} | {row['dataset']:<9} | "
            f"{row['chunk_recall_5']:>6.1%}     | {row['chunk_recall_10']:>6.1%}      | {row['chunk_mrr']:>8.3f}   | "
            f"{row['kp_recall_5']:>5.1%}   | {row['kp_recall_10']:>5.1%}    | {row['kp_mrr']:>6.3f}  | "
            f"{row['lat_p50']:.3f}s / {row['lat_p95']:.3f}s"
        )

    return table_a_results


def run_table_b_end_to_end():
    print("\n==================================================================")
    print("TASK 1 - TABLE B: END-TO-END EVALUATION (EXACTLY 4 RUNS)")
    print("==================================================================")

    runs = [
        ("Run 1: Baseline v1 (from cache)", GOLDEN_V1, False, False, False, False, "e2e_run1_baseline_v1.json"),
        ("Run 2: All Improvements on v1", GOLDEN_V1, True, False, False, False, "e2e_run2_improvements_v1.json"),
        ("Run 3: Baseline on Held-out v2", GOLDEN_V2, False, False, False, False, "e2e_run3_baseline_v2.json"),
        ("Run 4: All Improvements on Held-out v2", GOLDEN_V2, True, False, False, False, "e2e_run4_improvements_v2.json"),
    ]

    table_b_results = []

    for name, dpath, dl, sb, qe, te, fname in runs:
        settings.DENSE_TOP_K = 10
        settings.BM25_TOP_K = 10
        settings.SECTION_BOOST_ENABLED = sb
        settings.QUERY_EXPANSION_ENABLED = qe
        settings.DETERMINISTIC_LOOKUP_ENABLED = dl
        settings.TABLE_EXEMPTION_ENABLED = te

        out_path = RESULTS_DIR / fname
        res = run_evaluation(
            dataset_path=dpath,
            retrieval_only=False,
            no_judge=True,  # Judge not headline metric per Task 5
            output_path=out_path,
            update_markdown=False,
        )

        m = res["metrics"]
        num = m.get("numeric_accuracy", {})
        ref = m.get("refusal", {})
        grd = m.get("grounding", {})
        lat = m.get("latency_sec", {})
        c_stats = m.get("cache_stats", {})

        table_b_results.append({
            "run": name,
            "dataset": "v1 (n=53)" if "v1" in str(dpath) else "v2 (n=53)",
            "num_acc_overall": num.get("overall", 0.0),
            "num_acc_injected": num.get("injected_facts", 0.0),
            "num_acc_det": num.get("deterministic_lookup", 0.0),
            "num_acc_not_injected": num.get("not_injected", 0.0),
            "refusal_acc": ref.get("accuracy", 0.0),
            "false_refusal_rate": ref.get("false_refusal_rate", 0.0),
            "unverified_rate": grd.get("unverified_number_rate", 0.0),
            "lat_p50": lat.get("p50", 0.0),
            "lat_p95": lat.get("p95", 0.0),
            "cache_hits": c_stats.get("hits", 0),
            "cache_misses": c_stats.get("misses", 0),
            "regenerated_items": c_stats.get("regenerated_items", []),
        })

    print("\n--- TABLE B RESULTS SUMMARY ---")
    print(f"{'Run':<38} | {'Num Acc Overall':<16} | {'Injected':<9} | {'Det Lookup':<11} | {'Not Injected':<13} | {'False Refusal':<14} | {'Refusal Acc':<12} | {'Unverified %':<13} | {'Latency p50/p95':<16} | {'Cache (Hit/Miss)'}")
    print("-" * 175)
    for r in table_b_results:
        print(
            f"{r['run']:<38} | "
            f"{r['num_acc_overall']:>6.1%}           | "
            f"{r['num_acc_injected']:>6.1%}  | "
            f"{r['num_acc_det']:>6.1%}     | "
            f"{r['num_acc_not_injected']:>6.1%}       | "
            f"{r['false_refusal_rate']:>6.1%}        | "
            f"{r['refusal_acc']:>6.1%}       | "
            f"{r['unverified_rate']:>6.1%}       | "
            f"{r['lat_p50']:.3f}s / {r['lat_p95']:.3f}s   | "
            f"Hits: {r['cache_hits']}, Miss: {r['cache_misses']}"
        )
        if r['regenerated_items']:
            print(f"  -> Regenerated items ({len(r['regenerated_items'])}): {r['regenerated_items']}")

    return table_b_results


if __name__ == "__main__":
    t_a = run_table_a_retrieval()
    t_b = run_table_b_end_to_end()
    all_out = {"table_a": t_a, "table_b": t_b}
    (RESULTS_DIR / "phase_4c_tables.json").write_text(json.dumps(all_out, indent=2), encoding="utf-8")
    print("\nSaved all Phase 4c table results to backend/eval/results/phase_4c_tables.json")
