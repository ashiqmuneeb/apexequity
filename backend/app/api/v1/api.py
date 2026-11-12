from fastapi import APIRouter

from app.api.v1.endpoints import analysis, articles, system

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(articles.router)
api_router.include_router(analysis.router)

