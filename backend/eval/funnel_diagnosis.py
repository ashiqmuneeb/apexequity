import json
import sys
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.retrieval_service import retrieval_service  # noqa: E402


def load_corpus_data():
    col = retrieval_service.get_collection()
    res = col.get(include=["documents", "metadatas"])
    return res["ids"], res["documents"], res["metadatas"]


def find_gold_chunks_for_item(item: dict[str, Any], corpus_ids: list[str], corpus_docs: list[str], corpus_metas: list[dict[str, Any]]) -> list[str]:
    ticker = item["ticker"]
    passage = item.get("supporting_passage", "")
    qid = item["id"]

    # Specific grounded passages for v2 where supporting_passage wasn't pre-filled in jsonl
    v2_evidence_anchors = {
        "qual_v2_msft_supplier": ["qualified suppliers", "datacenter", "disruptions"],
        "qual_v2_googl_mfg": ["contract manufacturers", "technical infrastructure", "servers"],
        "qual_v2_aapl_supplier_capacity": ["single or limited-source", "component suppliers", "capacity constraints"],
        "qual_v2_nvda_networking": ["infiniband and ethernet", "network adapters", "switch"],
        "qual_v2_aapl_patent_lit": ["intellectual property", "patent", "licensing"],
        "qual_v2_googl_antitrust": ["antitrust", "regulatory", "department of justice"],
        "qual_v2_amd_instinct": ["amd instinct", "accelerators", "mi300"],
        "qual_v2_msft_gaming": ["activision blizzard", "gaming", "xbox"],
        "qual_v2_aapl_dma_eu": ["digital markets act", "european union", "app store"],
        "qual_v2_amd_foundry_atmp": ["foundry", "atmp", "packaging"],
    }

    words = [w.lower() for w in passage.split() if len(w) > 3] if passage else []
    matches = []

    for cid, d, m in zip(corpus_ids, corpus_docs, corpus_metas):
        if m.get("ticker") != ticker:
            continue
        d_lower = d.lower()

        if passage and passage.lower() in d_lower:
            matches.append(cid)
        elif words:
            overlap = sum(1 for w in words if w in d_lower) / len(words)
            if overlap >= 0.8:
                matches.append(cid)
        elif qid in v2_evidence_anchors:
            anchors = v2_evidence_anchors[qid]
            # Match chunk containing primary anchors
            if sum(1 for a in anchors if a.lower() in d_lower) >= 2:
                matches.append(cid)

    return matches


def trace_item_funnel(item: dict[str, Any], gold_ids: list[str], dense_k: int = 20, bm25_k: int = 20):
    ticker = item["ticker"]
    query = item["question"]

    # 1. Dense top-20
    col = retrieval_service.get_collection()
    embed_model = retrieval_service._get_embed_model()
    q_emb = embed_model.get_query_embedding(query)
    dense_res = col.query(query_embeddings=[q_emb], n_results=dense_k, where={"ticker": ticker}, include=["documents", "metadatas", "distances"])
    dense_ids = dense_res["ids"][0] if dense_res and dense_res["ids"] else []

    # 2. BM25 top-20
    bm25, chunk_records = retrieval_service._get_or_build_bm25(ticker)
    tokenized_q = retrieval_service._tokenize(query)
    scores = bm25.get_scores(tokenized_q)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:bm25_k]
    bm25_ids = [chunk_records[idx]["id"] for idx in top_indices if scores[idx] > 0]

    # 3. Fused candidates
    candidates = retrieval_service.retrieve_candidates_for_ticker(ticker, query, dense_top_k=dense_k, bm25_top_k=bm25_k)
    fused_ids = [c["id"] for c in candidates]

    # 4. Rerank
    _ = retrieval_service.rerank_and_select(query, candidates, top_n=dense_k)
    reranked_ids = [c["id"] for c in candidates]

    # Best rank among gold chunks
    def best_rank(rank_list: list[str]):
        ranks = [rank_list.index(gid) + 1 for gid in gold_ids if gid in rank_list]
        return min(ranks) if ranks else None

    d_rank = best_rank(dense_ids)
    b_rank = best_rank(bm25_ids)
    f_rank = best_rank(fused_ids)
    r_rank = best_rank(reranked_ids)

    return d_rank, b_rank, f_rank, r_rank


def run_full_diagnosis():
    corpus_ids, corpus_docs, corpus_metas = load_corpus_data()

    v1_items = [json.loads(line) for line in open(BACKEND_DIR / "eval" / "golden.jsonl", encoding="utf-8") if line.strip()]
    v1_qual = [x for x in v1_items if x.get("category") == "qualitative"]

    v2_items = [json.loads(line) for line in open(BACKEND_DIR / "eval" / "golden_v2_heldout.jsonl", encoding="utf-8") if line.strip()]
    v2_qual = [x for x in v2_items if x.get("category") == "qualitative"]

    print("==========================================================================================")
    print("TASK 2 & 8: RETRIEVAL FUNNEL DIAGNOSIS ACROSS FAILING QUALITATIVE ITEMS (V1 & V2)")
    print("==========================================================================================")

    failing_items_to_diagnose = [
        # v1 failures
        "qual_nvda_1", "qual_nvda_network", "qual_msft_2", "qual_aapl_1", "qual_aapl_3",
        "qual_aapl_hard_single_source", "qual_googl_3", "qual_amd_1", "qual_amd_3",
        # v2 failures
        "qual_v2_nvda_networking", "qual_v2_amd_instinct",
    ]

    all_qual = {x["id"]: (x, "v1") for x in v1_qual}
    all_qual.update({x["id"]: (x, "v2") for x in v2_qual})

    classification_counts = {
        "not in candidate pool (pool/recall problem)": 0,
        "in pool but dropped by the reranker (reranker problem)": 0,
        "in top-5 but key phrases not matched (metric problem)": 0,
        "no gold chunk found (bad key phrases or dataset problem)": 0,
    }

    diagnosis_rows = []

    for qid in failing_items_to_diagnose:
        item, benchmark_ver = all_qual[qid]
        ticker = item["ticker"]
        gold_ids = find_gold_chunks_for_item(item, corpus_ids, corpus_docs, corpus_metas)

        if not gold_ids:
            cat = "no gold chunk found (bad key phrases or dataset problem)"
            d_rank, b_rank, f_rank, r_rank = None, None, None, "dropped"
        else:
            d_rank, b_rank, f_rank, r_rank = trace_item_funnel(item, gold_ids, dense_k=20, bm25_k=20)
            in_pool = (d_rank is not None) or (b_rank is not None)
            if not in_pool:
                cat = "not in candidate pool (pool/recall problem)"
            elif r_rank is None or (isinstance(r_rank, int) and r_rank > 5):
                cat = "in pool but dropped by the reranker (reranker problem)"
            else:
                cat = "in top-5 but key phrases not matched (metric problem)"

        classification_counts[cat] += 1
        r_rank_display = str(r_rank) if r_rank is not None else "dropped"
        diagnosis_rows.append({
            "id": qid,
            "ver": benchmark_ver,
            "ticker": ticker,
            "gold_chunks": gold_ids,
            "dense_rank": str(d_rank) if d_rank else "None",
            "bm25_rank": str(b_rank) if b_rank else "None",
            "fused_rank": str(f_rank) if f_rank else "None",
            "rerank_rank": r_rank_display,
            "classification": cat,
        })

    print(f"\n{'Query ID':<28} | {'Ver':<3} | {'Ticker':<5} | {'Dense-20':<8} | {'BM25-20':<7} | {'Fused':<6} | {'Rerank':<7} | {'Classification'}")
    print("-" * 125)
    for r in diagnosis_rows:
        print(f"{r['id']:<28} | {r['ver']:<3} | {r['ticker']:<5} | {r['dense_rank']:<8} | {r['bm25_rank']:<7} | {r['fused_rank']:<6} | {r['rerank_rank']:<7} | {r['classification']}")

    print("\n--- Failure Classification Summary Counts ---")
    for cat, cnt in classification_counts.items():
        print(f"  * {cat}: {cnt}")

    return diagnosis_rows, classification_counts


if __name__ == "__main__":
    run_full_diagnosis()

