# ruff: noqa: E402
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from eval.run import run_evaluation


EVAL_DIR = BACKEND_DIR / "eval"
GOLDEN_V1 = EVAL_DIR / "golden.jsonl"
GOLDEN_V2 = EVAL_DIR / "golden_v2_heldout.jsonl"
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_all_ablations():
    print("==================================================================")
    print("STARTING PHASE 4b SYSTEMATIC ABLATION EXPERIMENTS")
    print("==================================================================")

    # 1. Ablation 2: Table Chunk Exemption only (pool 10, no boost, no expansion, no det)
    print("\n--- Running Ablation 2: Table Chunk Exemption Only ---")
    settings.DENSE_TOP_K = 10
    settings.BM25_TOP_K = 10
    settings.SECTION_BOOST_ENABLED = False
    settings.QUERY_EXPANSION_ENABLED = False
    settings.DETERMINISTIC_LOOKUP_ENABLED = False
    settings.TABLE_EXEMPTION_ENABLED = True
    run_evaluation(
        dataset_path=GOLDEN_V1,
        retrieval_only=True,
        output_path=RESULTS_DIR / "ablation_v1_table_exemption.json",
        update_markdown=False,
    )

    # 2. Ablation 3: Candidate Pool 20 Dense + 20 BM25 (no boost, no expansion, no det)
    print("\n--- Running Ablation 3: Pool 20 Dense + 20 BM25 ---")
    settings.DENSE_TOP_K = 20
    settings.BM25_TOP_K = 20
    settings.SECTION_BOOST_ENABLED = False
    settings.QUERY_EXPANSION_ENABLED = False
    settings.DETERMINISTIC_LOOKUP_ENABLED = False
    settings.TABLE_EXEMPTION_ENABLED = True
    run_evaluation(
        dataset_path=GOLDEN_V1,
        retrieval_only=True,
        output_path=RESULTS_DIR / "ablation_v1_pool20.json",
        update_markdown=False,
    )

    # 3. Ablation 4: Query Expansion + Section Boost (pool 10, no det)
    print("\n--- Running Ablation 4: Query Expansion + Section Boost ---")
    settings.DENSE_TOP_K = 10
    settings.BM25_TOP_K = 10
    settings.SECTION_BOOST_ENABLED = True
    settings.QUERY_EXPANSION_ENABLED = True
    settings.DETERMINISTIC_LOOKUP_ENABLED = False
    settings.TABLE_EXEMPTION_ENABLED = True
    run_evaluation(
        dataset_path=GOLDEN_V1,
        retrieval_only=True,
        output_path=RESULTS_DIR / "ablation_v1_query_boost.json",
        update_markdown=False,
    )

    # 4. Ablation 5: Deterministic Metric Lookup (pool 10, no boost, no expansion)
    print("\n--- Running Ablation 5: Deterministic Metric Lookup ---")
    settings.DENSE_TOP_K = 10
    settings.BM25_TOP_K = 10
    settings.SECTION_BOOST_ENABLED = False
    settings.QUERY_EXPANSION_ENABLED = False
    settings.DETERMINISTIC_LOOKUP_ENABLED = True
    settings.TABLE_EXEMPTION_ENABLED = True
    run_evaluation(
        dataset_path=GOLDEN_V1,
        retrieval_only=True,
        output_path=RESULTS_DIR / "ablation_v1_det_lookup.json",
        update_markdown=False,
    )

    # 5. All Improvements on v1 (Retrieval-Only first for quick verification)
    print("\n--- Running All Improvements on v1 (Retrieval-Only) ---")
    settings.DENSE_TOP_K = 20
    settings.BM25_TOP_K = 20
    settings.SECTION_BOOST_ENABLED = True
    settings.QUERY_EXPANSION_ENABLED = True
    settings.DETERMINISTIC_LOOKUP_ENABLED = True
    settings.TABLE_EXEMPTION_ENABLED = True
    run_evaluation(
        dataset_path=GOLDEN_V1,
        retrieval_only=True,
        output_path=RESULTS_DIR / "v1_all_improvements_retrieval.json",
        update_markdown=False,
    )

    # 6. v2 Held-out Baseline (All improvements OFF)
    print("\n--- Running v2 Held-Out Baseline (All improvements OFF) ---")
    settings.DENSE_TOP_K = 10
    settings.BM25_TOP_K = 10
    settings.SECTION_BOOST_ENABLED = False
    settings.QUERY_EXPANSION_ENABLED = False
    settings.DETERMINISTIC_LOOKUP_ENABLED = False
    settings.TABLE_EXEMPTION_ENABLED = False
    run_evaluation(
        dataset_path=GOLDEN_V2,
        retrieval_only=True,
        output_path=RESULTS_DIR / "v2_heldout_baseline.json",
        update_markdown=False,
    )

    # 7. v2 Held-out with All Improvements
    print("\n--- Running v2 Held-Out with All Improvements ---")
    settings.DENSE_TOP_K = 20
    settings.BM25_TOP_K = 20
    settings.SECTION_BOOST_ENABLED = True
    settings.QUERY_EXPANSION_ENABLED = True
    settings.DETERMINISTIC_LOOKUP_ENABLED = True
    settings.TABLE_EXEMPTION_ENABLED = True
    run_evaluation(
        dataset_path=GOLDEN_V2,
        retrieval_only=True,
        output_path=RESULTS_DIR / "v2_heldout_all_improvements.json",
        update_markdown=False,
    )

    print("\n==================================================================")
    print("ALL RETRIEVAL ABLATIONS COMPLETED SUCCESSFULLY")
    print("==================================================================")


if __name__ == "__main__":
    run_all_ablations()

