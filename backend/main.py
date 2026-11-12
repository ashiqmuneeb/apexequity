"""
Entrypoint runner for the Financial Stock Analysis FastAPI application.
Run via: uvicorn app.main:app --reload
or: python main.py
"""
import uvicorn
from app.core.config import settings
from app.main import app

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
