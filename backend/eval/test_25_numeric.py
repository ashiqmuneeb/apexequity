import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.deterministic_lookup import deterministic_lookup_service  # noqa: E402
from eval.metrics import check_numeric_match  # noqa: E402


v1 = [json.loads(line) for line in open(BACKEND_DIR / "eval" / "golden.jsonl", encoding="utf-8") if line.strip()]
v1_num = [x for x in v1 if x.get("category") == "numeric"]

print("=== EVALUATION OF ALL 25 NUMERIC V1 ITEMS (TASK 4) ===\n")
header = f"{'ID':<20} | {'Ticker':<6} | {'Path':<14} | {'Match':<7} | {'Expected':<10} | {'Report Summary'}"
print(header)
print("-" * len(header))

correct_count = 0
det_count = 0
rag_count = 0
failures = []

for item in v1_num:
    qid = item["id"]
    ticker = item["ticker"]
    question = item["question"]
    exp_val = float(item["expected_value"])
    unit = item.get("unit", "")

    det_rep, sources, is_refusal = deterministic_lookup_service.check_deterministic_lookup(ticker, question)
    if det_rep is not None:
        path = "deterministic"
        det_count += 1
        rep = det_rep
    else:
        path = "rag"
        rag_count += 1
        rep = "Dispatched to RAG path"

    matched, reason = check_numeric_match(rep, exp_val, unit)
    if matched:
        correct_count += 1
    else:
        failures.append((qid, ticker, exp_val, unit, path, reason, rep))

    status_str = "PASS" if matched else "FAIL"
    print(f"{qid:<20} | {ticker:<6} | {path:<14} | {status_str:<7} | {exp_val} {unit:<6} | {rep[:50]}...")

print("\nSummary:")
print(f"Total numeric items: {len(v1_num)}")
print(f"Answered by Deterministic Path: {det_count}/{len(v1_num)}")
print(f"Dispatched to RAG Path: {rag_count}/{len(v1_num)}")
print(f"Matched Correctly: {correct_count}/{len(v1_num)} ({correct_count / len(v1_num) * 100:.1f}%)")
print(f"Failures: {len(failures)}")
for f in failures:
    print(f"  FAILURE: {f[0]} ({f[1]}): Expected {f[2]} {f[3]} | Path: {f[4]} | Reason: {f[5]}")

