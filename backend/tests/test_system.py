def test_healthz(client):
    """Verifies basic healthz endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_system_status(client):
    """Verifies system status endpoint structure and model metadata."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "has_groq_key" in data
    assert "index_initialized" in data
    assert "indexed_articles_count" in data
    assert "models" in data
    assert "Groq" in data["models"]["llm"]


def test_key_config_validation(client):
    """Verifies that empty API key payloads are rejected."""
    response = client.post("/api/v1/config/key", json={"groq_api_key": "   "})
    assert response.status_code == 400

