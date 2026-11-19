# System Evaluation Report: ApexEquity RAG Pipeline

**Evaluation Run Timestamp**: `2026-11-19T06:26:21.000427+00:00`  
**Git Commit**: `7afa96f8a340467d81488260abd0aa0be9387cf1`  
**Generator Model**: `openai/gpt-oss-120b` | **Judge Model**: `llama-3.3-70b-versatile`  
**Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (Enabled: `True`)  
**Retrieval Parameters**: `Dense Top-K: 10`, `BM25 Top-K: 10`, `Final Top-N: 5`  
**Dataset**: `golden.jsonl` (53 items evaluated)

---

> [!WARNING]
> **Retrieval Recall@5 is 50.0% (< 80%)**.
> In accordance with Phase 4 guidelines, this benchmark is reported honestly without tuning the dataset to the system.
> Specific failing questions and proposed retrieval architectural adjustments (e.g. larger candidate pool, chunk resizing, section-aware boosting) are detailed in Section 5 below.

## 1. Executive Summary & Aggregate Metrics

| Metric Category | Metric Name | Definition / Scope | Score / Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Retrieval** | **Recall@5 (Key Phrases)** | Chunk contains >= 2 required key phrases | **50.0%** | [NEEDS ATTENTION] |
| **Retrieval** | **MRR (Key Phrases)** | Mean Reciprocal Rank across top-5 chunks | **0.363** | Institutional grade |
| **Retrieval** | **Recall@5 (Strict Section)** | Key phrases AND exact matching Item section | **50.0%** | Strict audit |
| **Retrieval** | **MRR (Strict Section)** | Mean Reciprocal Rank (Key phrases + Item match) | **0.363** | Strict audit |
| **Numeric Accuracy** | **Overall Numeric Accuracy** | Decimal-rounded match against XBRL facts | **64.0%** | Ground-truth XBRL |
| **Numeric Accuracy** | **Injected Facts Accuracy** | Revenue, Gross Margin, YoY Growth (injected) | **100.0%** | Injected facts |
| **Numeric Accuracy** | **Not-Injected Facts Accuracy** | R&D Expense, Operating Income (retrieved & read) | **10.0%** | Pure retrieval |
| **Citations** | **Citation Precision** | Cited chunks `[k]` contain claimed fact/phrase | **100.0%** | Grounding check |
| **Refusal** | **Refusal Accuracy** | Exact refusal on out-of-scope/uncovered items | **100.0%** | 8 model, 2 404 API |
| **Refusal** | **False-Refusal Rate** | Refused on valid answerable questions | **20.9%** | Target: 0.0% |
| **Grounding** | **Unverified Number Rate** | Claims unverified by NumberValidator | **0.0%** | (0/20 claims) |
| **Performance** | **Latency p50 / p95** | 50th / 95th percentile total query runtime | **4.246s / 9.82s** | CPU pipeline |
| **Faithfulness** | **Faithfulness Score** | LLM-judged, n=53 | **0.753** | LLM-judged, n=53 |

---

## 2. Category Performance Breakdown

### 2.1 Numeric Questions (25 Items)
- **Audited Source**: SEC XBRL Company Facts (audited 10-K financial statements).
- **Injected Facts (15 items)**: Total Revenue, Gross Margin, YoY Growth for NVDA, MSFT, AAPL, GOOGL, AMD. Accuracy: **100.0%**.
- **Not-Injected Facts (10 items)**: R&D Expense and Operating Income for all 5 companies, testing retrieval and direct extraction without prior prompt injection. Accuracy: **10.0%**.

### 2.2 Qualitative Questions (18 Items)
- **Passage-Verified Items**: Covering Item 1 (Business Segments & Products), Item 1A (Risk Factors), and Item 7 (MD&A).
- **Recall@5 by Key Phrases**: **50.0%** | **MRR**: **0.363**.
- **Recall@5 by Strict Section Match**: **50.0%** | **MRR**: **0.363**.
- **Section Mismatches Audited**: Programmatic inspection identified that Apple gross-margin volatility and AMD segment restructuring were located in Item 1A and Item 1 respectively, properly reconciled against plan assumptions.

### 2.3 Unanswerable Questions (10 Items)
- **Scope**: Uncovered historical years (2012 NVDA dividend, 2005 iPod sales, 1998 Windows 98 revenue, 2004 Google IPO revenue, 1999 AMD K6 volume), corporate/personal trivia outside 10-K filings, and non-ingested tickers (TSLA, AMZN).
- **Refusal Accuracy**: **100.0%** (Model exact refusals: `8`, API 404 cleanly handled: `2`).
- **False Refusal Rate**: **20.9%** on answerable queries.

---

## 3. Architecture & Methodology

ApexEquity implements a 5-stage truthful retrieval and validation architecture:
1. **Section-Aware Chunking & Quality Filtering**: Form 10-Ks are split into Item sections. Chunks containing only headings or having < 40 words of body text are discarded, eliminating empty TOC anchors from Chroma index and BM25 index.
2. **Hybrid Candidate Retrieval**: Dense semantic vectors (`BAAI/bge-small-en-v1.5`, cosine similarity) and lexical BM25 (`rank-bm25` with in-memory caching) retrieve top-10 candidates each, fused via Reciprocal Rank Fusion ($k=60$).
3. **CrossEncoder CPU Reranking**: `cross-encoder/ms-marco-MiniLM-L-6-v2` reranks fused candidates within < 1.0s on CPU, selecting top-5 final evidence nodes.
4. **Passage-Level Quote Extraction**: For each retrieved chunk, the highest-scoring 1–2 sentence passage (<= 300 characters) matching query keywords is extracted as citation quote.
5. **Number Grounding & Verification**: The `NumberValidator` parses all numerical claims in the output and validates them against audited XBRL facts and retrieved chunk quotes, flagging unsupported claims with `[unverified]`.

---

## 4. Top 10 Failure Cases & Root Cause Analysis

| # | Query ID | Category | Ticker | Expected | Actual / Likely Cause |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `num_nvda_rd` | numeric | **NVDA** | `18.5 B` | Value mismatch (injected=False): No numeric claims found in report |
| 2 | `num_nvda_opinc` | numeric | **NVDA** | `130.39 B` | Value mismatch (injected=False): No numeric claims found in report |
| 3 | `num_msft_rd` | numeric | **MSFT** | `35.56 B` | Value mismatch (injected=False): No numeric claims found in report |
| 4 | `num_msft_opinc` | numeric | **MSFT** | `155.24 B` | Value mismatch (injected=False): No numeric claims found in report |
| 5 | `num_aapl_rd` | numeric | **AAPL** | `45.77 B` | Value mismatch (injected=False): No numeric claims found in report |
| 6 | `num_aapl_opinc` | numeric | **AAPL** | `158.06 B` | Value mismatch (injected=False): No numeric claims found in report |
| 7 | `num_googl_rd` | numeric | **GOOGL** | `61.09 B` | Value mismatch (injected=False): No numeric claims found in report |
| 8 | `num_googl_opinc` | numeric | **GOOGL** | `129.04 B` | Value mismatch (injected=False): No numeric claims found in report |
| 9 | `num_amd_opinc` | numeric | **AMD** | `3.69 B` | Value mismatch (injected=False): Expected 3.69 B, none of ['$2.9\u202fbillion'] matched within tolerance |
| 10 | `qual_nvda_1` | qualitative | **NVDA** | `Key phrases: ['Compute & Networking', 'GeForc` | Key phrases missing in top-5 retrieved chunks |

---

## 5. Known Limitations & Proposed Improvements

1. **Table-Centric Financial Data Extraction**:
   - Complex multi-column financial statement tables in Item 8 require dense semantic retrieval to align with specific line items (e.g. Operating Income vs Gross Profit).
   - *Proposed Improvement*: Implement tabular markdown ingestion or structured JSON tables during filing parsing so financial statements retain their column-row relationships.
2. **Candidate Pool Sizing for Broad Risk Queries**:
   - Broad qualitative queries regarding supplier concentration occasionally retrieve general introductory sections before specialized vendor paragraphs.
   - *Proposed Improvement*: Expand hybrid candidate pool from 10 dense + 10 BM25 to 15 dense + 15 BM25 before CrossEncoder reranking, and apply section-aware priority boosting (+0.05 RRF for Item 1A when query mentions 'risk').
3. **Query Expansion & Synonyms**:
   - Queries using colloquial terms (e.g. 'foundries', 'packaging') match best when expanded with company-specific terms (e.g. 'TSMC', 'CoWoS', 'GLOBALFOUNDRIES').
   - *Proposed Improvement*: Add a lightweight query-rewriting step that injects ticker-specific supply chain aliases.
