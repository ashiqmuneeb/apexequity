import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Provides a TestClient fixture configured for the FastAPI app."""
    return TestClient(app)

