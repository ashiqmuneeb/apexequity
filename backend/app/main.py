from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logger import logger

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise RAG Engine for Financial Stock Analysis with LlamaIndex & Groq",
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registrations (supports both /api/v1 and legacy /api)
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")


@app.get("/healthz", tags=["System & Configuration"])
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "version": settings.VERSION}


# Mount production frontend build if present
if settings.FRONTEND_DIST_DIR.exists():
    assets_dir = settings.FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("api/v1/"):
            raise HTTPException(status_code=404, detail="API route not found.")
        file_path = settings.FRONTEND_DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(settings.FRONTEND_DIST_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

