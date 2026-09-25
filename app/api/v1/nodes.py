from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, require_admin
from app.services.node_service import NodeService
from app.schemas.node import StorageNodeResponse, ClusterStatsResponse
from app.models.user import User

# Standard node router
router = APIRouter(prefix="/nodes", tags=["Node Manager & Cluster Health"])

# Admin protected node router (strictly requiring ADMIN role)
admin_node_router = APIRouter(prefix="/admin/nodes", tags=["Admin Cluster Administration"])


# --- Admin Protected Endpoints ---
@admin_node_router.get("", response_model=List[StorageNodeResponse])
async def admin_list_nodes(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: list all registered storage nodes with full metadata."""
    service = NodeService(db)
    return await service.list_nodes()


@admin_node_router.get("/stats", response_model=ClusterStatsResponse)
async def admin_get_cluster_stats(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: cluster statistics and storage utilization."""
    service = NodeService(db)
    health = await service.get_cluster_health()
    return ClusterStatsResponse(
        total_nodes=health["total_nodes"],
        healthy_nodes=health["healthy_nodes"],
        degraded_nodes=health["degraded_nodes"],
        failed_nodes=health["failed_nodes"],
        total_capacity_bytes=health["total_capacity_bytes"],
        used_capacity_bytes=health["used_capacity_bytes"],
        utilization_percent=health["utilization_percent"],
        total_objects=0,
        total_replicas=0,
        active_repair_jobs=0,
    )


@admin_node_router.post("/sweep", response_model=List[Dict[str, Any]])
@router.post("/sweep", response_model=List[Dict[str, Any]])
async def trigger_heartbeat_sweep(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to perform active heartbeat sweep and update node states."""
    service = NodeService(db)
    events = await service.check_and_update_node_heartbeats()
    await db.commit()
    return events


# --- General / Dashboard Endpoints ---
@router.get("", response_model=List[StorageNodeResponse])
async def list_nodes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List storage nodes."""
    service = NodeService(db)
    return await service.list_nodes()


@router.get("/cluster/health")
async def get_cluster_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete cluster-wide health status and zone matrix."""
    service = NodeService(db)
    return await service.get_cluster_health()


@router.get("/{node_id}/health")
async def get_node_health(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve realtime health and capacity for an individual storage node."""
    service = NodeService(db)
    return await service.get_node_health(node_id)
