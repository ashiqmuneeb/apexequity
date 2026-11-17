from app.core.config import settings


def test_admin_endpoints_require_api_key(client):
    """Verifies that mutating endpoints return 403 Forbidden without valid X-API-Key."""
    # 1. POST /api/v1/articles
    res1 = client.post(
        "/api/v1/articles",
        json={"ticker": "UNAUTH", "content": "Unauthorized content"},
    )
    assert res1.status_code == 403
    assert "Admin access forbidden" in res1.json()["detail"]

    # 2. DELETE /api/v1/articles/{ticker}
    res2 = client.delete("/api/v1/articles/UNAUTH")
    assert res2.status_code == 403
    assert "Admin access forbidden" in res2.json()["detail"]

    # 3. POST /api/v1/articles/fetch-live
    res3 = client.post("/api/v1/articles/fetch-live", json={"ticker": "UNAUTH"})
    assert res3.status_code == 403
    assert "Admin access forbidden" in res3.json()["detail"]

    # 4. POST /api/v1/index/rebuild
    res4 = client.post("/api/v1/index/rebuild")
    assert res4.status_code == 403
    assert "Admin access forbidden" in res4.json()["detail"]


def test_admin_endpoints_succeed_with_api_key(client):
    """Verifies that requests with valid X-API-Key are authorized."""
    admin_headers = {"X-API-Key": settings.ADMIN_API_KEY}
    test_ticker = "SECAUTH"
    test_content = (
        "SecAuth Corp test filing content with verifiable metrics for tests."
    )

    # 1. Save with admin header
    save_res = client.post(
        "/api/v1/articles",
        json={"ticker": test_ticker, "content": test_content},
        headers=admin_headers,
    )
    assert save_res.status_code == 200

    # 2. Delete with admin header
    del_res = client.delete(
        f"/api/v1/articles/{test_ticker}",
        headers=admin_headers,
    )
    assert del_res.status_code == 200


def test_config_key_endpoint_removed(client):
    """Verifies that POST /api/v1/config/key has been completely removed from production."""
    res = client.post("/api/v1/config/key", json={"groq_api_key": "gsk_test123"})
    assert res.status_code == 404 or res.status_code == 405


def test_demo_endpoints_return_sample_flag(client):
    """Verifies that GET /api/v1/demo/{name} returns structured sample data with is_sample: true."""
    # 1. Single stock demo
    single_res = client.get("/api/v1/demo/single")
    assert single_res.status_code == 200
    data = single_res.json()
    assert data["is_sample"] is True
    assert data["ticker"] == "NVDA"
    assert "sample_notice" in data

    # 2. Compare demo
    compare_res = client.get("/api/v1/demo/compare")
    assert compare_res.status_code == 200
    cdata = compare_res.json()
    assert cdata["is_sample"] is True
    assert cdata["stock_a"] == "NVDA"
    assert cdata["stock_b"] == "GOOGL"

    # 3. Coverage demo
    coverage_res = client.get("/api/v1/demo/coverage")
    assert coverage_res.status_code == 200
    cov_data = coverage_res.json()
    assert cov_data["is_sample"] is True
    assert len(cov_data["companies"]) > 0

    # 4. Non-existent demo returns 404
    missing_res = client.get("/api/v1/demo/nonexistent")
    assert missing_res.status_code == 404


def test_cors_allowlist_configuration():
    """Verifies that CORS origins are explicitly parsed from environment."""
    origins = settings.get_allowed_origins()
    assert isinstance(origins, list)
    assert "*" not in origins
    assert "http://localhost:5173" in origins

