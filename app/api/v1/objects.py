from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.services.storage_service import StorageService
from app.schemas.storage import ObjectResponse, ObjectDetailResponse
from app.models.user import User

router = APIRouter(prefix="/buckets/{bucket_name}/objects", tags=["Objects"])


@router.get("", response_model=List[ObjectResponse])
async def list_objects(
    bucket_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StorageService(db)
    return await service.list_objects(current_user, bucket_name)


@router.get("/{key}/details", response_model=ObjectDetailResponse)
async def get_object_details(
    bucket_name: str,
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StorageService(db)
    return await service.get_object_details(current_user, bucket_name, key)
