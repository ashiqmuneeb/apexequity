def test_analysis_request_validation(client):
    """Verifies that invalid requests without ticker are rejected with 422."""
    response = client.post("/api/v1/analyze/single", json={})
    assert response.status_code == 422


def test_comparison_request_validation(client):
    """Verifies that requests missing stock_b are rejected with 422."""
    response = client.post(
        "/api/v1/analyze/compare",
        json={"stock_a": "NVDA"},
    )
    assert response.status_code == 422


def test_custom_query_validation(client):
    """Verifies that empty query requests are rejected."""
    response = client.post("/api/v1/analyze/custom", json={})
    assert response.status_code == 422

