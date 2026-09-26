"""
Objects API: Concurrent Upload, Resilient Download, Versioning, and Deep Replica Inspection
"""

from typing import List, Optional, Dict, Any
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.models.bucket import Bucket
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectEntity, ObjectVersion, ObjectReplica
from backend.app.services.data_pipeline import write_object, read_object, delete_object_tombstone

router = APIRouter(prefix="/buckets/{bucket_name}/objects", tags=["Objects"])


class ObjectListItem(BaseModel):
    id: str
    key: str
    version_num: int
    size_bytes: int
    content_type: str
    checksum_sha256: str
    storage_policy: str
    is_deleted: bool
    created_at: str
    replica_count: int


@router.get("", response_model=List[ObjectListItem])
async def list_objects(
    bucket_name: str,
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b_stmt = select(Bucket).where(Bucket.name == bucket_name)
    b_res = await db.execute(b_stmt)
    bucket = b_res.scalar_one_or_none()
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    stmt = (
        select(ObjectEntity)
        .where(ObjectEntity.bucket_id == bucket.id)
        .options(
            selectinload(ObjectEntity.versions).selectinload(ObjectVersion.replicas)
        )
    )
    if not include_deleted:
        stmt = stmt.where(ObjectEntity.is_deleted == False)

    res = await db.execute(stmt)
    entities = res.scalars().all()

    items = []
    for ent in entities:
        if not ent.versions:
            continue
        latest_v = sorted(ent.versions, key=lambda v: v.version_num, reverse=True)[0]
        if not include_deleted and latest_v.is_tombstone:
            continue

        items.append(
            ObjectListItem(
                id=str(ent.id),
                key=ent.key,
                version_num=latest_v.version_num,
                size_bytes=latest_v.size_bytes,
                content_type=latest_v.content_type,
                checksum_sha256=latest_v.checksum_sha256,
                storage_policy=latest_v.storage_policy,
                is_deleted=latest_v.is_tombstone,
                created_at=latest_v.created_at.isoformat(),
                replica_count=len([r for r in latest_v.replicas if r.status == "HEALTHY"]),
            )
        )
    return items


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_object(
    bucket_name: str,
    key: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b_stmt = select(Bucket).where(Bucket.name == bucket_name)
    b_res = await db.execute(b_stmt)
    bucket = b_res.scalar_one_or_none()
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")

    object_key = key or file.filename or "unnamed_object"
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"

    version = await write_object(
        db,
        bucket=bucket,
        key=object_key,
        data=data,
        content_type=content_type,
    )

    return {
        "status": "UPLOADED",
        "bucket": bucket_name,
        "key": object_key,
        "version_num": version.version_num,
        "size_bytes": version.size_bytes,
        "checksum_sha256": version.checksum_sha256,
        "replicas_placed": len(version.replicas),
        "durability_policy": bucket.durability_policy,
    }


@router.get("/{key:path}")
async def download_object(
    bucket_name: str,
    key: str,
    version_num: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if download or metadata
    if key.endswith("/details"):
        # Redirect internally to details
        real_key = key[:-8]
        return await get_object_details(bucket_name, real_key, db, current_user)

    data_bytes, version = await read_object(
        db,
        bucket_name=bucket_name,
        key=key,
        version_num=version_num,
    )

    filename = key.split("/")[-1]
    safe_filename = quote(filename)

    return Response(
        content=data_bytes,
        media_type=version.content_type,
        headers={
            "Content-Length": str(len(data_bytes)),
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "X-NexVault-Version": str(version.version_num),
            "X-Content-SHA256": version.checksum_sha256,
            "X-Durability-Policy": version.storage_policy,
        },
    )


@router.delete("/{key:path}")
async def delete_object(
    bucket_name: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tombstone = await delete_object_tombstone(db, bucket_name=bucket_name, key=key)
    return {
        "deleted": True,
        "bucket": bucket_name,
        "key": key,
        "tombstone_version": tombstone.version_num,
        "message": f"Object soft-deleted with tombstone v{tombstone.version_num}. Historical versions preserved.",
    }


@router.get("/{key:path}/details")
async def get_object_details(
    bucket_name: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Advanced Object Details: Full version history, physical node locations,
    replica health matrix, zones, and SHA-256 verification status.
    """
    b_stmt = select(Bucket).where(Bucket.name == bucket_name)
    b_res = await db.execute(b_stmt)
    bucket = b_res.scalar_one_or_none()
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    stmt = (
        select(ObjectEntity)
        .where(ObjectEntity.bucket_id == bucket.id, ObjectEntity.key == key)
        .options(
            selectinload(ObjectEntity.versions).selectinload(ObjectVersion.replicas)
        )
    )
    res = await db.execute(stmt)
    obj_entity = res.scalar_one_or_none()
    if not obj_entity or not obj_entity.versions:
        raise HTTPException(status_code=404, detail=f"Object '{key}' not found")

    # Fetch nodes dictionary
    nodes_res = await db.execute(select(StorageNode))
    nodes_dict = {n.id: n for n in nodes_res.scalars().all()}

    versions_list = []
    latest_v = sorted(obj_entity.versions, key=lambda v: v.version_num, reverse=True)[0]

    for v in sorted(obj_entity.versions, key=lambda v: v.version_num, reverse=True):
        replicas_info = []
        healthy_count = 0
        for r in v.replicas:
            node = nodes_dict.get(r.node_id)
            node_up = node and node.status in ("HEALTHY", "RECOVERING") and not node.is_simulated_partitioned
            is_healthy = r.status == "HEALTHY" and node_up
            if is_healthy:
                healthy_count += 1

            replicas_info.append({
                "replica_id": str(r.id),
                "node_id": r.node_id,
                "node_name": node.name if node else "Unknown Node",
                "zone": node.zone if node else "Unknown",
                "port": node.port if node else 0,
                "node_status": node.status if node else "OFFLINE",
                "node_partitioned": node.is_simulated_partitioned if node else False,
                "blob_id": r.blob_id,
                "replica_status": r.status,
                "stored_checksum": r.stored_checksum,
                "last_verified_at": r.last_verified_at.isoformat(),
                "error_detail": r.error_detail,
            })

        # Availability state for this version
        rf = bucket.replication_factor
        if healthy_count >= rf:
            avail_state = "OPTIMAL"
        elif healthy_count > 0:
            avail_state = "DEGRADED"
        else:
            avail_state = "CRITICAL_OFFLINE"

        versions_list.append({
            "version_id": str(v.id),
            "version_num": v.version_num,
            "size_bytes": v.size_bytes,
            "content_type": v.content_type,
            "checksum_sha256": v.checksum_sha256,
            "is_tombstone": v.is_tombstone,
            "storage_policy": v.storage_policy,
            "created_at": v.created_at.isoformat(),
            "availability_state": avail_state,
            "healthy_replicas_count": healthy_count,
            "required_replication_factor": rf,
            "replicas": replicas_info,
        })

    return {
        "object_id": str(obj_entity.id),
        "bucket": bucket_name,
        "key": key,
        "is_deleted": obj_entity.is_deleted,
        "current_version_num": latest_v.version_num,
        "durability_policy": bucket.durability_policy,
        "versions": versions_list,
    }
