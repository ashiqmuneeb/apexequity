def test_list_articles(client):
    """Verifies that the article listing endpoint returns indexed files."""
    response = client.get("/api/v1/articles")
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert isinstance(data["articles"], list)
    assert len(data["articles"]) > 0

    # Verify article item attributes
    first = data["articles"][0]
    assert "ticker" in first
    assert "filename" in first
    assert "preview" in first
    assert "content" in first


def test_save_and_delete_article(client):
    """Verifies creating and deleting an article document."""
    test_ticker = "TESTXYZ"
    test_content = "This is a temporary test financial summary for unit testing."

    # 1. Save article
    save_resp = client.post(
        "/api/v1/articles",
        json={"ticker": test_ticker, "content": test_content},
    )
    assert save_resp.status_code == 200
    assert "saved successfully" in save_resp.json()["message"]

    # 2. Delete article
    del_resp = client.delete(f"/api/v1/articles/{test_ticker}")
    assert del_resp.status_code == 200
    assert "deleted successfully" in del_resp.json()["message"]


def test_fetch_live_stock_validation(client):
    """Verifies that empty ticker requests to live fetch are rejected."""
    resp = client.post("/api/v1/articles/fetch-live", json={"ticker": ""})
    assert resp.status_code == 400

