from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io
from app.api.deps import get_db, get_current_user
from app.services.storage_service import StorageService
from app.schemas.storage import (
    ObjectResponse,
    ObjectDetailResponse,
    ObjectVersionResponse,
)
from app.models.user import User

router = APIRouter(prefix="/buckets/{bucket_name}/objects", tags=["Objects"])


@router.post("/upload", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
async def upload_object(
    bucket_name: str,
    file: UploadFile = File(...),
    key: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Uploads object bytes, replicates across Zone A and Zone B nodes, records SHA-256."""
    object_key = key.strip() if key and key.strip() else file.filename
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    service = StorageService(db)
    result = await service.upload_object(
        current_user=current_user,
        bucket_name=bucket_name,
        key=object_key,
        data=content,
        content_type=content_type,
    )
    await db.commit()
    return result


@router.get("", response_model=List[ObjectResponse])
async def list_objects(
    bucket_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active (non-tombstoned) objects in bucket."""
    service = StorageService(db)
    return await service.list_objects(current_user, bucket_name)


# Specific sub-routes MUST precede greedy {key:path}
@router.get("/{key:path}/details", response_model=ObjectDetailResponse)
async def get_object_details(
    bucket_name: str,
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete object metadata, versions, and physical replica locations/statuses."""
    service = StorageService(db)
    return await service.get_object_details(current_user, bucket_name, key)


@router.get("/{key:path}/metadata", response_model=ObjectResponse)
async def get_object_metadata(
    bucket_name: str,
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active object metadata and latest version info."""
    service = StorageService(db)
    return await service.get_object_metadata(current_user, bucket_name, key)


@router.get("/{key:path}/versions", response_model=List[ObjectVersionResponse])
async def get_object_versions(
    bucket_name: str,
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all versions including historical versions and deletion tombstones."""
    service = StorageService(db)
    return await service.get_object_versions(current_user, bucket_name, key)


@router.get("/{key:path}")
async def download_object(
    bucket_name: str,
    key: str,
    version: Optional[int] = Query(None, description="Optional version number to download"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloads object bytes from a verified healthy physical replica with checksum check."""
    service = StorageService(db)
    data, content_type, checksum, filename = await service.download_object(
        current_user=current_user,
        bucket_name=bucket_name,
        key=key,
        version_num=version,
    )
    await db.commit()

    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-NEXVAULT-Checksum-SHA256": checksum,
            "Content-Length": str(len(data)),
        },
    )


@router.delete("/{key:path}")
async def delete_object(
    bucket_name: str,
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes an object by creating a tombstone version, keeping auditability intact."""
    service = StorageService(db)
    result = await service.delete_object(current_user, bucket_name, key)
    await db.commit()
    return result
