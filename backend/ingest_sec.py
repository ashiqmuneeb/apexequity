"""
Standalone SEC EDGAR Ingestion and Indexing Script for ApexEquity.
Fetches, caches, extracts 10-K filings and XBRL facts for NVDA, MSFT, AAPL, GOOGL, AMD.
Run via: python ingest_sec.py
"""

import json
import os
import re
import sys
from pathlib import Path


# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.core.logger import logger  # noqa: E402
from app.services.article_service import article_service  # noqa: E402
from app.services.sec_service import (  # noqa: E402
    TARGET_COMPANIES,
    sec_ingestion_service,
    validate_user_agent,
)


def main():
    print("=" * 80)
    print("ApexEquity — SEC EDGAR Ingestion & Audited XBRL Extraction")
    print("=" * 80)

    # 1. Validate SEC User-Agent (Condition 1)
    raw_ua = settings.SEC_EDGAR_USER_AGENT or os.getenv("SEC_EDGAR_USER_AGENT")
    try:
        validated_ua = validate_user_agent(raw_ua)
        # Never print full real email in console logs
        email_part = validated_ua.split()[-1] if validated_ua else ""
        masked_email = email_part[:2] + "***@" + email_part.split("@")[-1] if "@" in email_part else "***"
        print(f"[*] SEC User-Agent validated: {validated_ua.split()[0]} <{masked_email}>")
    except ValueError as ve:
        print(f"[!] INGESTION FAILED: {ve}", file=sys.stderr)
        sys.exit(1)

    articles_dir = settings.ARTICLES_DIR
    articles_dir.mkdir(parents=True, exist_ok=True)
    storage_dir = settings.STORAGE_DIR
    storage_dir.mkdir(parents=True, exist_ok=True)

    ingested_metrics = {}
    ingested_docs = {}
    item_diagnostics = {}

    # 2. Ingest NVDA, MSFT, AAPL, GOOGL, AMD (Conditions 2, 7, 8)
    print("\n[+] Ingesting 10-K filings and XBRL disclosures from SEC EDGAR...")
    try:
        for ticker, info in TARGET_COMPANIES.items():
            cik = info["cik"]
            print(f"    -> Processing {ticker} (CIK: {cik}, {info['name']})...")
            metrics, full_doc, char_counts = sec_ingestion_service.ingest_ticker(ticker, cik)
            ingested_metrics[ticker] = metrics
            ingested_docs[ticker] = full_doc
            item_diagnostics[ticker] = char_counts
            print(
                f"       Parsed 10-K {metrics['revenue_period']}: "
                f"Revenue={metrics['revenue_label']}, Gross Margin={metrics['margin_label']}, "
                f"Accn={metrics['accession_number']}"
            )
    except Exception as e:
        print(f"\n[!] Ingestion error encountered: {e}", file=sys.stderr)
        print("[!] Existing corpus preserved. Aborting ingestion.", file=sys.stderr)
        sys.exit(1)

    # 3. Write new 10-K files to backend/articles/
    written_files = []
    try:
        for ticker, doc_text in ingested_docs.items():
            filename = f"{ticker}_10K.txt"
            file_path = articles_dir / filename
            file_path.write_text(doc_text, encoding="utf-8")
            written_files.append(file_path)
        print(f"\n[+] Successfully wrote {len(written_files)} official 10-K filing files.")
    except Exception as e:
        print(f"\n[!] Failed to write 10-K files: {e}", file=sys.stderr)
        print("[!] Preserving legacy files and aborting.", file=sys.stderr)
        sys.exit(1)

    # 4. Safe Corpus Cleanup (Condition 3): Delete NVDA.txt and MSFT.txt only after 10-K files are written
    for old_file in ["NVDA.txt", "MSFT.txt"]:
        old_path = articles_dir / old_file
        if old_path.exists():
            old_path.unlink()
            print(f"    [-] Removed hand-written summary: {old_file}")

    # 5. Label AMD.txt (Condition 4)
    amd_path = articles_dir / "AMD.txt"
    if amd_path.exists():
        amd_content = amd_path.read_text(encoding="utf-8")
        if "[DOCUMENT_SOURCE: Yahoo Finance snapshot (undated)]" not in amd_content:
            labeled_content = (
                "[DOCUMENT_SOURCE: Yahoo Finance snapshot (undated)]\n"
                "[NOTE: Undated Yahoo Finance snapshot kept for historical reference. Excluded from 10-K index.]\n\n"
                + amd_content
            )
            amd_path.write_text(labeled_content, encoding="utf-8")
            print("    [*] Labeled AMD.txt as 'Yahoo Finance snapshot (undated)'.")

    # 6. Save audited XBRL metrics store
    try:
        settings.SEC_METRICS_FILE.write_text(
            json.dumps(ingested_metrics, indent=2), encoding="utf-8"
        )
        print(f"    [*] Persisted grounded SEC metrics to {settings.SEC_METRICS_FILE.name}")
    except Exception as e:
        logger.warning(f"Failed to persist SEC metrics store: {e}")

    # 7. Rebuild vector embeddings index (Condition 4: AMD.txt is excluded automatically)
    print("\n[+] Rebuilding vector index in ./storage (excluding AMD.txt)...")
    try:
        chunk_count, indexed_files = article_service.build_and_persist_index(force_rebuild=True)
        print(f"    [+] Indexed {chunk_count} chunk(s) across {len(indexed_files)} files: {', '.join(indexed_files)}")
    except Exception as e:
        print(f"[!] Warning during vector re-indexing: {e}", file=sys.stderr)

    # 8. Diagnostics: File size in KB, character count per item, first 15 lines of Item 1A (Condition 2)
    print("\n" + "=" * 80)
    print("10-K Document Parsing Diagnostics (Item 1, 1A, 7, 8)")
    print("=" * 80)
    for ticker in TARGET_COMPANIES.keys():
        file_path = articles_dir / f"{ticker}_10K.txt"
        size_kb = file_path.stat().st_size / 1024.0 if file_path.exists() else 0.0
        counts = item_diagnostics.get(ticker, {})

        print(f"\n--- {ticker}_10K.txt ({size_kb:.1f} KB) ---")
        for item_name in ["Item 1", "Item 1A", "Item 7", "Item 8"]:
            c_len = counts.get(item_name, 0)
            if c_len > 0:
                print(f"  * {item_name}: {c_len:,} characters")
            else:
                print(f"  * {item_name}: NOT FOUND as separate section (stated explicitly in file)")

        # First 15 lines of Item 1A
        doc_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        item_1a_match = re.search(r"===\s*ITEM 1A\s*===\n(.*?)(?:\n===\s*ITEM|\Z)", doc_content, re.DOTALL)
        if item_1a_match:
            item_1a_text = item_1a_match.group(1).strip()
            first_15 = "\n".join(item_1a_text.splitlines()[:15])
            print("  [First 15 lines of Item 1A]:")
            for line in first_15.splitlines():
                print(f"    | {line[:100]}")
        else:
            print("  [Item 1A not located for excerpt preview]")

    # 9. Verification Table against sec.gov (Condition 6 & 8)
    print("\n" + "=" * 80)
    print("AUDITED SEC XBRL FINANCIAL METRICS VERIFICATION TABLE")
    print("=" * 80)
    header = f"{'Ticker':<7} {'Company':<24} {'FY / End Date':<24} {'Revenue':<10} {'Gross Margin':<14} {'Accession Number'}"
    print(header)
    print("-" * len(header))

    for ticker, m in ingested_metrics.items():
        period_str = f"FY{m['fiscal_year']} ({m['period_end_date']})"
        margin_str = f"{m['margin_label']} ({m['margin_tag']})"
        print(
            f"{ticker:<7} {m['company_name'][:23]:<24} {period_str:<24} "
            f"{m['revenue_label']:<10} {margin_str:<14} {m['accession_number']}"
        )

    print("=" * 80)
    print("[✓] Phase 2 SEC EDGAR Ingestion & Verification complete.")


if __name__ == "__main__":
    main()
