from fastapi import APIRouter

from app.api.v1.endpoints import analysis, articles, demo, system


api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(articles.router)
api_router.include_router(analysis.router)
api_router.include_router(demo.router)
