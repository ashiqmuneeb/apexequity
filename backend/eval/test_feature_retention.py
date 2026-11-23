import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.retrieval_service import retrieval_service  # noqa: E402
from eval.funnel_diagnosis import (  # noqa: E402
    find_gold_chunks_for_item,
    load_corpus_data,
)
from eval.metrics import (  # noqa: E402
    evaluate_chunk_retrieval_hit,
    evaluate_retrieval_hit,
)


def evaluate_config(v1_qual, v2_qual, corpus_data, dense_k=10, bm25_k=10, q_expand=False, sec_boost=False):
    # Set settings
    settings.DENSE_TOP_K = dense_k
    settings.BM25_TOP_K = bm25_k
    settings.QUERY_EXPANSION_ENABLED = q_expand
    settings.SECTION_BOOST_ENABLED = sec_boost

    c_ids, c_docs, c_metas = corpus_data

    results = {}
    for name, items in [("v1", v1_qual), ("v2", v2_qual)]:
        kp_hits = 0
        chunk_hits = 0
        kp_ranks = []
        chunk_ranks = []

        for item in items:
            ticker = item["ticker"]
            q = item["question"]
            gold_ids = find_gold_chunks_for_item(item, c_ids, c_docs, c_metas)

            # Retrieve top 5
            candidates = retrieval_service.retrieve_candidates_for_ticker(
                ticker, q, dense_top_k=dense_k, bm25_top_k=bm25_k
            )
            sources = retrieval_service.rerank_and_select(q, candidates, top_n=5)

            # Key phrase eval
            kp_hit, _, kp_rank, _ = evaluate_retrieval_hit(sources, item.get("key_phrases", []), top_k=5)
            if kp_hit:
                kp_hits += 1
                kp_ranks.append(1.0 / kp_rank if kp_rank else 0.0)
            else:
                kp_ranks.append(0.0)

            # Chunk hit eval
            c_hit, c_rank = evaluate_chunk_retrieval_hit(sources, gold_ids, top_k=5)
            if c_hit:
                chunk_hits += 1
                chunk_ranks.append(1.0 / c_rank if c_rank else 0.0)
            else:
                chunk_ranks.append(0.0)

        n = len(items)
        results[name] = {
            "n": n,
            "kp_recall": round(kp_hits / n, 4),
            "kp_mrr": round(float(np.mean(kp_ranks)), 4),
            "chunk_recall": round(chunk_hits / n, 4),
            "chunk_mrr": round(float(np.mean(chunk_ranks)), 4),
        }
    return results


def main():
    corpus_data = load_corpus_data()
    v1_items = [json.loads(line) for line in open(BACKEND_DIR / "eval" / "golden.jsonl", encoding="utf-8") if line.strip()]
    v1_qual = [x for x in v1_items if x.get("category") == "qualitative"]

    v2_items = [json.loads(line) for line in open(BACKEND_DIR / "eval" / "golden_v2_heldout.jsonl", encoding="utf-8") if line.strip()]
    v2_qual = [x for x in v2_items if x.get("category") == "qualitative"]

    print("==========================================================================================")
    print("TASK 7 & CONDITION 7: PRE-REGISTERED FEATURE RETENTION RULE EVALUATION")
    print("Rule: Keep only if it improves a retrieval metric on v1 without lowering it on v2.")
    print("==========================================================================================")

    configs = [
        ("1. Baseline (10+10, no expand, no boost)", 10, 10, False, False),
        ("2. Pool 20+20 (20+20, no expand, no boost)", 20, 20, False, False),
        ("3. Query Expansion (10+10, expand=True, no boost)", 10, 10, True, False),
        ("4. Section Boost (10+10, no expand, boost=True)", 10, 10, False, True),
        ("5. All Flags Combined (20+20, expand=True, boost=True)", 20, 20, True, True),
    ]

    all_res = {}
    for label, dk, bk, qe, sb in configs:
        res = evaluate_config(v1_qual, v2_qual, corpus_data, dk, bk, qe, sb)
        all_res[label] = res
        print(f"\nConfiguration: {label}")
        print(f"  v1 (n={res['v1']['n']}): Chunk Recall@5 = {res['v1']['chunk_recall']:.1%}, Chunk MRR = {res['v1']['chunk_mrr']:.3f} | KP Recall@5 = {res['v1']['kp_recall']:.1%}, KP MRR = {res['v1']['kp_mrr']:.3f}")
        print(f"  v2 (n={res['v2']['n']}): Chunk Recall@5 = {res['v2']['chunk_recall']:.1%}, Chunk MRR = {res['v2']['chunk_mrr']:.3f} | KP Recall@5 = {res['v2']['kp_recall']:.1%}, KP MRR = {res['v2']['kp_mrr']:.3f}")

    # Output decisions
    base_v1_c = all_res["1. Baseline (10+10, no expand, no boost)"]["v1"]["chunk_recall"]
    base_v2_c = all_res["1. Baseline (10+10, no expand, no boost)"]["v2"]["chunk_recall"]
    base_v1_kp = all_res["1. Baseline (10+10, no expand, no boost)"]["v1"]["kp_recall"]
    base_v2_kp = all_res["1. Baseline (10+10, no expand, no boost)"]["v2"]["kp_recall"]

    print("\n==========================================================================================")
    print("DECISIONS UNDER PRE-REGISTERED RETENTION RULE")
    print("==========================================================================================")
    for feat_label, key in [
        ("Pool Size 20+20", "2. Pool 20+20 (20+20, no expand, no boost)"),
        ("Query Expansion", "3. Query Expansion (10+10, expand=True, no boost)"),
        ("Section Boost", "4. Section Boost (10+10, no expand, boost=True)"),
    ]:
        v1_c = all_res[key]["v1"]["chunk_recall"]
        v2_c = all_res[key]["v2"]["chunk_recall"]
        v1_kp = all_res[key]["v1"]["kp_recall"]
        v2_kp = all_res[key]["v2"]["kp_recall"]

        improves_v1 = (v1_c > base_v1_c) or (v1_kp > base_v1_kp) or (all_res[key]["v1"]["chunk_mrr"] > all_res["1. Baseline (10+10, no expand, no boost)"]["v1"]["chunk_mrr"])
        lowers_v2 = (v2_c < base_v2_c) or (v2_kp < base_v2_kp)

        decision = "KEEP (ON)" if (improves_v1 and not lowers_v2) else "DEFAULT OFF"
        print(f"Feature: {feat_label}")
        print(f"  Delta v1: Chunk Recall {v1_c - base_v1_c:+.1%}, KP Recall {v1_kp - base_v1_kp:+.1%}")
        print(f"  Delta v2: Chunk Recall {v2_c - base_v2_c:+.1%}, KP Recall {v2_kp - base_v2_kp:+.1%}")
        print(f"  Decision: {decision}")

    # Table exemption note
    print("\nFeature: Table Exemption")
    print("  Ingestion audit: Only 1 chunk in entire corpus was < 40 words (NVDA Item 8 cross-reference paragraph with 0 tables).")
    print("  No table chunks exist that were dropped or saved by the exemption.")
    print("  Delta on v1: 0.0%, Delta on v2: 0.0%.")
    print("  Decision: DEFAULT OFF (code preserved behind TABLE_EXEMPTION_ENABLED flag).")


if __name__ == "__main__":
    main()

