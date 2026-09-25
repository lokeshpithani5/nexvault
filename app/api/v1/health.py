from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.api.deps import get_db
from app.core.config import settings
from app.core.database import active_db_type
from app.repositories.node_repository import NodeRepository

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/v1/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "UNKNOWN"
    try:
        await db.execute(text("SELECT 1"))
        db_status = f"CONNECTED ({active_db_type})"
    except Exception as e:
        db_status = f"FAILED ({e})"

    node_repo = NodeRepository(db)
    nodes = await node_repo.list_all()
    node_summary = {
        "registered": len(nodes),
        "healthy": sum(1 for n in nodes if n.status == "HEALTHY" and not n.is_simulated_partitioned),
    }

    return {
        "status": "HEALTHY" if "CONNECTED" in db_status else "DEGRADED",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
        "storage_nodes": node_summary,
    }
