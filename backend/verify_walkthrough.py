# ruff: noqa: E402
import json
import logging
import sys
import time
from pathlib import Path


# Configure path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.analysis_service import analysis_service
from app.services.number_validator import number_validator


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("walkthrough_runner")

output_data = {}

print("==================================================")
print("1. QUERY (A): NVIDIA Supply Chain Risks")
print("==================================================")
q_a = "What are NVIDIA's main supply chain risks?"
res_a = analysis_service.custom_query(q_a)
print(f"Report:\n{res_a.report}\n")
print(f"Sources count: {len(res_a.sources)}")
item_1a_cited = False
for i, s in enumerate(res_a.sources, 1):
    print(f"[{i}] Ticker={s.ticker}, Section={s.section}, Form={s.form}, Retrieval={s.retrieval_score:.4f}, Rerank={s.rerank_score}")
    print(f"    Quote: {s.quote[:140]}...")
    if "1A" in (s.section or ""):
        item_1a_cited = True

output_data["query_a"] = {
    "prompt": q_a,
    "report": res_a.report,
    "sources": [s.model_dump() for s in res_a.sources],
    "item_1a_cited": item_1a_cited,
    "unsupported_numbers": res_a.unsupported_numbers,
}

time.sleep(2)

print("\n==================================================")
print("2. QUERY (B): NVIDIA 2012 Quarterly Dividend (Refusal Check)")
print("==================================================")
q_b = "What was NVIDIA's quarterly dividend in 2012?"
res_b = analysis_service.custom_query(q_b)
print(f"Report:\n{res_b.report}\n")
print(f"Is exact refusal: {res_b.report.strip() == 'Not disclosed in the retrieved filings.'}")
output_data["query_b"] = {
    "prompt": q_b,
    "report": res_b.report,
    "is_exact_refusal": res_b.report.strip() == "Not disclosed in the retrieved filings.",
    "sources_count": len(res_b.sources),
}

time.sleep(2)

print("\n==================================================")
print("3. QUERY (C): NVDA vs MSFT Comparison Isolation")
print("==================================================")
res_c = analysis_service.compare_stocks("NVDA", "MSFT")
print(f"Report snippet:\n{res_c.report[:400]}...\n")
print(f"Total sources: {len(res_c.sources)}")
nvda_sources = [s for s in res_c.sources if s.ticker == "NVDA"]
msft_sources = [s for s in res_c.sources if s.ticker == "MSFT"]
print(f"NVDA sources count: {len(nvda_sources)}, MSFT sources count: {len(msft_sources)}")

# Check for cross contamination
clean_separation = (
    len(res_c.sources) == 10
    and all(s.ticker == "NVDA" for s in res_c.sources[:5])
    and all(s.ticker == "MSFT" for s in res_c.sources[5:])
)
print(f"Clean strict source separation: {clean_separation}")

output_data["query_c"] = {
    "prompt": res_c.prompt,
    "report": res_c.report,
    "sources": [s.model_dump() for s in res_c.sources],
    "clean_separation": clean_separation,
    "unsupported_numbers": res_c.unsupported_numbers,
}

time.sleep(2)

print("\n==================================================")
print("4. QUERY (D): NVDA Single Stock Dossier & Number Grounding")
print("==================================================")
res_d = analysis_service.analyze_single_stock("NVDA")
print(f"Report:\n{res_d.report}\n")
print(f"Unsupported numbers count: {len(res_d.unsupported_numbers)}")
print(f"Unsupported numbers: {res_d.unsupported_numbers}")

# Detailed breakdown of all numbers found in the text
raw_claims = number_validator.extract_claims(res_d.report)
claim_details = []
for c in raw_claims:
    is_unsupported = any(c.raw_text in un or un in c.raw_text for un in res_d.unsupported_numbers)
    claim_details.append({
        "raw": c.raw_text,
        "value": c.value,
        "is_percentage": c.has_percent,
        "unit": c.unit,
        "unsupported": is_unsupported,
    })

print(f"Total number claims extracted: {len(claim_details)}")
print(f"Claims flagged as unverified: {sum(1 for c in claim_details if c['unsupported'])}")

claim_75 = [c for c in claim_details if abs(c["value"] - 75.0) < 0.1 and c["is_percentage"]]
print(f"75.0% claim present: {len(claim_75) > 0}")
if claim_75:
    for c in claim_75:
        print(f"  -> Raw: '{c['raw']}', Flagged: {c['unsupported']}")

output_data["query_d"] = {
    "report": res_d.report,
    "unsupported_numbers": res_d.unsupported_numbers,
    "total_claims_count": len(claim_details),
    "unsupported_claims_count": sum(1 for c in claim_details if c["unsupported"]),
    "claim_details": claim_details,
    "sources": [s.model_dump() for s in res_d.sources],
}

# Save output
with open("backend/storage/walkthrough_results.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print("\nSaved walkthrough results to backend/storage/walkthrough_results.json")

