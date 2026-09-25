from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_admin
from app.services.node_service import NodeService
from app.schemas.node import StorageNodeResponse, ClusterStatsResponse
from app.models.user import User

router = APIRouter(prefix="/admin/nodes", tags=["Admin Nodes & Cluster"])


@router.get("", response_model=List[StorageNodeResponse])
async def list_cluster_nodes(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = NodeService(db)
    return await service.list_nodes()


@router.get("/stats", response_model=ClusterStatsResponse)
async def get_cluster_stats(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = NodeService(db)
    return await service.get_cluster_stats()
