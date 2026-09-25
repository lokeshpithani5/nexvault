from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.buckets import router as buckets_router
from app.api.v1.objects import router as objects_router
from app.api.v1.nodes import router as nodes_router
from app.api.v1.chaos import router as chaos_router
from app.api.v1.events import router as events_router
from app.api.v1.repairs import router as repairs_router
from app.api.v1.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(buckets_router)
api_v1_router.include_router(objects_router)
api_v1_router.include_router(nodes_router)
api_v1_router.include_router(chaos_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(repairs_router)
api_v1_router.include_router(health_router)
