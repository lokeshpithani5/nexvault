"""
Buckets API: Namespace management, Durability Configuration, and Capacity Accounting
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.models.bucket import Bucket
from backend.app.models.object import ObjectEntity, ObjectVersion
from backend.app.services.event_logger import log_event

router = APIRouter(prefix="/buckets", tags=["Buckets"])


class CreateBucketRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=63, pattern="^[a-z0-9][a-z0-9.-]*[a-z0-9]$")
    replication_factor: int = Field(default=3, ge=1, le=6)
    durability_policy: Optional[str] = "REPLICATION_3X"


class BucketResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    replication_factor: int
    durability_policy: str
    object_count: int
    total_bytes: int
    created_at: str


@router.get("", response_model=List[BucketResponse])
async def list_buckets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List accessible buckets with aggregated object counts and bytes used."""
    stmt = (
        select(Bucket)
        .options(
            selectinload(Bucket.objects).selectinload(ObjectEntity.versions)
        )
    )
    # Admin sees all buckets; standard user sees all or owned buckets
    if current_user.role != "ADMIN":
        stmt = stmt.where(Bucket.owner_id == current_user.id)

    res = await db.execute(stmt)
    buckets = res.scalars().all()

    response = []
    for b in buckets:
        # Count non-tombstone objects and sum sizes of latest versions
        active_objects = [o for o in b.objects if not o.is_deleted]
        total_size = 0
        for o in active_objects:
            latest_v = sorted(o.versions, key=lambda v: v.version_num, reverse=True)
            if latest_v and not latest_v[0].is_tombstone:
                total_size += latest_v[0].size_bytes

        response.append(
            BucketResponse(
                id=str(b.id),
                name=b.name,
                owner_id=str(b.owner_id),
                replication_factor=b.replication_factor,
                durability_policy=b.durability_policy,
                object_count=len(active_objects),
                total_bytes=total_size,
                created_at=b.created_at.isoformat(),
            )
        )
    return response


@router.post("", response_model=BucketResponse, status_code=status.HTTP_201_CREATED)
async def create_bucket(
    req: CreateBucketRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if bucket name already taken
    existing = await db.execute(select(Bucket).where(Bucket.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bucket with name '{req.name}' already exists",
        )

    # Determine durability policy
    policy = req.durability_policy
    if not policy:
        policy = f"REPLICATION_{req.replication_factor}X"

    bucket = Bucket(
        name=req.name,
        owner_id=current_user.id,
        replication_factor=req.replication_factor,
        durability_policy=policy,
    )
    db.add(bucket)
    await db.flush()

    await log_event(
        db,
        event_type="BUCKET_CREATED",
        severity="INFO",
        message=f"Bucket '{bucket.name}' created with RF={bucket.replication_factor} ({bucket.durability_policy}) by {current_user.email}",
    )
    await db.commit()

    return BucketResponse(
        id=str(bucket.id),
        name=bucket.name,
        owner_id=str(bucket.owner_id),
        replication_factor=bucket.replication_factor,
        durability_policy=bucket.durability_policy,
        object_count=0,
        total_bytes=0,
        created_at=bucket.created_at.isoformat(),
    )


@router.delete("/{name}", status_code=status.HTTP_200_OK)
async def delete_bucket(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b_res = await db.execute(
        select(Bucket)
        .where(Bucket.name == name)
        .options(selectinload(Bucket.objects))
    )
    bucket = b_res.scalar_one_or_none()
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{name}' not found")

    if current_user.role != "ADMIN" and bucket.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    active_objs = [o for o in bucket.objects if not o.is_deleted]
    if active_objs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bucket '{name}' is not empty ({len(active_objs)} active objects). Delete objects first.",
        )

    await db.delete(bucket)
    await log_event(
        db,
        event_type="BUCKET_DELETED",
        severity="WARNING",
        message=f"Bucket '{name}' was deleted by {current_user.email}",
    )
    await db.commit()
    return {"deleted": True, "bucket": name}
