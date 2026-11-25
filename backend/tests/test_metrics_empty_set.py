from eval.metrics import compute_aggregate_metrics
from eval.run import _fmt_float, _fmt_pct


def test_empty_records_returns_empty_dict():
    res = compute_aggregate_metrics([])
    assert res == {}


def test_numeric_only_records_empty_qualitative_and_unanswerable():
    # Like v3 held-out (numeric only)
    records = [
        {
            "id": "num_1",
            "category": "numeric",
            "injected": False,
            "path": "rag",
            "numeric_correct": True,
            "expected_value": 10.0,
            "latency_sec": 1.2,
            "is_refusal": False,
        },
        {
            "id": "num_2",
            "category": "numeric",
            "injected": False,
            "path": "rag",
            "numeric_correct": False,
            "expected_value": 20.0,
            "latency_sec": 1.4,
            "is_refusal": False,
        },
    ]
    metrics = compute_aggregate_metrics(records)

    # Retrieval metrics must be None, not 1.0
    retrieval = metrics["retrieval"]
    assert retrieval["chunk_recall_at_5"] is None
    assert retrieval["chunk_recall_at_10"] is None
    assert retrieval["chunk_mrr"] is None
    assert retrieval["recall_at_5_key_phrases"] is None
    assert retrieval["mrr_key_phrases"] is None
    assert retrieval["recall_at_5_raw"] is None
    assert retrieval["mrr_raw"] is None
    assert retrieval["recall_at_5_strict_item"] is None
    assert retrieval["mrr_strict_item"] is None

    # Refusal metrics must be None, not 1.0 or 18/18
    refusal = metrics["refusal"]
    assert refusal["accuracy"] is None
    assert refusal["refusals_by_model"] is None
    assert refusal["refusals_by_404_api"] is None
    assert refusal["false_refusal_rate"] == 0.0  # 0 false refusals / 2 answerable

    # Numeric accuracy is evaluated
    num_acc = metrics["numeric_accuracy"]
    assert num_acc["overall"] == 0.5
    assert num_acc["not_injected"] == 0.5
    assert num_acc["injected_facts"] is None
    assert num_acc["deterministic_lookup"] is None

    # Formatting helper outputs "n/a"
    assert _fmt_pct(retrieval["recall_at_5_key_phrases"]) == "n/a"
    assert _fmt_float(retrieval["mrr_key_phrases"]) == "n/a"
    assert _fmt_pct(refusal["accuracy"]) == "n/a"
    assert _fmt_pct(num_acc["injected_facts"]) == "n/a"
    assert _fmt_pct(num_acc["overall"]) == "50.0%"


def test_qualitative_only_records_empty_numeric_and_unanswerable():
    records = [
        {
            "id": "qual_1",
            "category": "qualitative",
            "chunk_hit_at_5": True,
            "chunk_rank": 1,
            "hit_a_norm_5": True,
            "rank_a_norm": 1,
            "hit_a_raw": True,
            "rank_a_raw": 1,
            "hit_b": True,
            "rank_b": 1,
            "latency_sec": 0.8,
            "is_refusal": False,
        }
    ]
    metrics = compute_aggregate_metrics(records)

    retrieval = metrics["retrieval"]
    assert retrieval["chunk_recall_at_5"] == 1.0
    assert retrieval["recall_at_5_key_phrases"] == 1.0
    assert retrieval["mrr_key_phrases"] == 1.0

    # Numeric accuracy must be None, not 0.0
    num_acc = metrics["numeric_accuracy"]
    assert num_acc["overall"] is None
    assert num_acc["injected_facts"] is None
    assert num_acc["deterministic_lookup"] is None
    assert num_acc["not_injected"] is None

    assert _fmt_pct(num_acc["overall"]) == "n/a"


def test_unanswerable_only_records_empty_answerable():
    records = [
        {
            "id": "unans_1",
            "category": "unanswerable",
            "refusal_correct": True,
            "refusal_by": "model",
            "is_refusal": True,
            "latency_sec": 0.5,
        }
    ]
    metrics = compute_aggregate_metrics(records)

    refusal = metrics["refusal"]
    assert refusal["accuracy"] == 1.0
    assert refusal["refusals_by_model"] == 1
    assert refusal["false_refusal_rate"] is None  # 0 answerable queries

    assert _fmt_pct(refusal["false_refusal_rate"]) == "n/a"
    assert _fmt_pct(refusal["accuracy"]) == "100.0%"

