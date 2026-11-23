import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.retrieval_service import retrieval_service  # noqa: E402
from eval.metrics import evaluate_retrieval_hit  # noqa: E402


def check_benchmark(path, name):
    items = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    qual = [x for x in items if x.get("category") == "qualitative"]
    print(f"=== {name} (total qual: {len(qual)}) ===")
    fails = []
    for x in qual:
        sources = retrieval_service.retrieve_single(x["ticker"], x["question"], top_n=5)
        hit_a, hit_b, r_a, r_b = evaluate_retrieval_hit(sources, x["key_phrases"], top_k=5)
        status = "PASS" if hit_a else "FAIL"
        if not hit_a:
            fails.append(x["id"])
        print(f"{x['id']}: {status} (rank={r_a}) kp={x['key_phrases'][:2]}")
    print(f"{name} Failing IDs ({len(fails)}): {fails}\n")
    return fails

if __name__ == "__main__":
    v1_fails = check_benchmark(BACKEND_DIR / "eval" / "golden.jsonl", "v1")
    v2_fails = check_benchmark(BACKEND_DIR / "eval" / "golden_v2_heldout.jsonl", "v2")

