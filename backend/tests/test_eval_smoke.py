import json
from unittest.mock import patch

from app.schemas.analysis import AnalysisResponse, SourceEvidenceNode
from eval.metrics import (
    check_numeric_match,
    evaluate_citation_precision,
    evaluate_retrieval_hit,
)
from eval.run import run_evaluation


def test_numeric_tolerance_matching():
    """Verifies that check_numeric_match mirrors number_validator decimal tolerance (Condition 2)."""
    # Ground truth is $215.94B
    report_exact = "NVIDIA reported total fiscal year 2026 revenue of $215.94 billion."
    matched, _ = check_numeric_match(report_exact, 215.94, unit="B")
    assert matched is True

    # 1 decimal rounding: $215.9B -> round(215.94, 1) == 215.9
    report_one_dec = "Total revenue reached $215.9 billion."
    matched, _ = check_numeric_match(report_one_dec, 215.94, unit="B")
    assert matched is True

    # Unit conversion: 18,497 million vs 18.50 billion
    report_millions = "Research and development expense was $18,497 million."
    matched, _ = check_numeric_match(report_millions, 18.50, unit="B")
    assert matched is True

    # Disagreeing number
    report_wrong = "Total revenue was $150.00 billion."
    matched, _ = check_numeric_match(report_wrong, 215.94, unit="B")
    assert matched is False


def test_retrieval_hit_evaluation():
    """Verifies retrieval hit under both Definition A (key phrases) and Definition B (strict section)."""
    sources = [
        SourceEvidenceNode(
            ticker="NVDA",
            section="Item 1",
            rank=1,
            quote="We report our business results in two segments: Compute & Networking and Graphics.",
            text="We report our business results in two segments: Compute & Networking and Graphics.",
        ),
        SourceEvidenceNode(
            ticker="NVDA",
            section="Item 1A",
            rank=2,
            quote="Supply chain disruptions could negatively impact our gross margins.",
            text="Supply chain disruptions could negatively impact our gross margins.",
        ),
    ]

    # Matching Item 1
    hit_a, hit_b, rank_a, rank_b = evaluate_retrieval_hit(
        sources=sources,
        key_phrases=["Compute & Networking", "business results in two segments"],
        target_item="Item 1",
        top_k=5,
    )
    assert hit_a is True
    assert hit_b is True
    assert rank_a == 1
    assert rank_b == 1

    # Mismatched Item section (key phrases match, but target is Item 7)
    hit_a_diff, hit_b_diff, rank_a_diff, rank_b_diff = evaluate_retrieval_hit(
        sources=sources,
        key_phrases=["Compute & Networking", "business results in two segments"],
        target_item="Item 7",
        top_k=5,
    )
    assert hit_a_diff is True
    assert hit_b_diff is False
    assert rank_a_diff == 1
    assert rank_b_diff is None


def test_citation_precision_evaluation():
    """Verifies citation precision computation for cited nodes."""
    sources = [
        SourceEvidenceNode(
            rank=1,
            quote="NVIDIA revenue reached $215.94 billion in fiscal year 2026.",
            text="NVIDIA revenue reached $215.94 billion in fiscal year 2026.",
        )
    ]
    valid_report = "Revenue was $215.94 billion in FY 2026 [1]."
    precision, verified, total = evaluate_citation_precision(valid_report, sources)
    assert total == 1
    assert verified == 1
    assert precision == 1.0


def test_eval_smoke_run_offline(tmp_path):
    """Offline smoke test evaluating 5 mock items with fake LLM and fake embeddings (Condition 5)."""
    # 5 Mock items across categories
    mock_dataset = [
        {
            "id": "smoke_num_injected",
            "category": "numeric",
            "ticker": "NVDA",
            "question": "What was NVIDIA revenue?",
            "injected": True,
            "expected_value": 215.94,
            "unit": "B",
        },
        {
            "id": "smoke_num_not_injected",
            "category": "numeric",
            "ticker": "NVDA",
            "question": "What was NVIDIA R&D expense?",
            "injected": False,
            "expected_value": 18.50,
            "unit": "B",
        },
        {
            "id": "smoke_qual",
            "category": "qualitative",
            "ticker": "NVDA",
            "question": "What are the segments?",
            "target_item": "Item 1",
            "key_phrases": ["Compute & Networking", "Graphics"],
        },
        {
            "id": "smoke_unans",
            "category": "unanswerable",
            "ticker": "NVDA",
            "question": "2012 dividend?",
        },
        {
            "id": "smoke_unans_404",
            "category": "unanswerable",
            "ticker": "TSLA",
            "question": "TSLA deliveries?",
            "is_uncovered_ticker": True,
        },
    ]

    golden_file = tmp_path / "golden.jsonl"
    with open(golden_file, "w", encoding="utf-8") as f:
        for item in mock_dataset:
            f.write(json.dumps(item) + "\n")

    mock_sources = [
        SourceEvidenceNode(
            ticker="NVDA",
            section="Item 1",
            rank=1,
            quote="Compute & Networking and Graphics segments generated $215.94B revenue and $18.50B R&D.",
            text="Compute & Networking and Graphics segments generated $215.94B revenue and $18.50B R&D.",
        )
    ]

    def mock_analyze(ticker, custom_prompt=""):
        if ticker == "TSLA":
            raise Exception("404: No documents ingested for ticker TSLA")
        if "2012" in custom_prompt:
            return AnalysisResponse(
                ticker=ticker,
                prompt=custom_prompt,
                report="Not disclosed in the retrieved filings.",
                sources=[],
                unsupported_numbers=[],
            )
        return AnalysisResponse(
            ticker=ticker,
            prompt=custom_prompt,
            report="Total revenue was $215.94 billion and R&D was $18.50B. Compute & Networking and Graphics [1].",
            sources=mock_sources,
            unsupported_numbers=[],
        )

    with (
        patch("eval.run.GOLDEN_PATH", golden_file),
        patch("eval.run.LATEST_JSON", tmp_path / "latest.json"),
        patch("eval.run.EVALUATION_MD", tmp_path / "EVALUATION.md"),
        patch("eval.run.analysis_service.analyze_single_stock", side_effect=mock_analyze),
        patch("eval.run.time.sleep", return_value=None),
    ):
        results = run_evaluation(limit=5, no_judge=True, no_cache=True, delay_sec=0.0)

        assert results["metadata"]["evaluated_items_count"] == 5
        metrics = results["metrics"]
        assert metrics["retrieval"]["recall_at_5_key_phrases"] == 1.0
        assert metrics["numeric_accuracy"]["injected_facts"] == 1.0
        assert metrics["numeric_accuracy"]["not_injected"] == 1.0
        assert metrics["refusal"]["accuracy"] == 1.0
        assert (tmp_path / "latest.json").exists()
        assert (tmp_path / "EVALUATION.md").exists()

