from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.user import User
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/admin/metrics", tags=["Admin Observability & Metrics"])


@router.get("", response_model=Dict[str, Any])
async def get_system_metrics(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Returns comprehensive calculated metrics from persistent database and node state."""
    service = MetricsService(db)
    return await service.get_system_metrics()


@router.get("/cluster", response_model=Dict[str, Any])
async def get_cluster_summary_metrics(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Returns concise dashboard-friendly cluster health and durability summary."""
    service = MetricsService(db)
    return await service.get_cluster_summary()
