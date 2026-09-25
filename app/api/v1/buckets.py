from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.services.storage_service import StorageService
from app.schemas.storage import BucketCreateRequest, BucketResponse, PolicyResponse
from app.models.user import User

router = APIRouter(prefix="/buckets", tags=["Buckets"])


@router.get("", response_model=List[BucketResponse])
async def list_buckets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StorageService(db)
    return await service.list_user_buckets(current_user)


@router.post("", response_model=BucketResponse, status_code=status.HTTP_201_CREATED)
async def create_bucket(
    bucket_in: BucketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StorageService(db)
    bucket = await service.create_bucket(current_user, bucket_in)
    await db.commit()
    return bucket


@router.get("/policies", response_model=List[PolicyResponse])
async def list_policies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StorageService(db)
    return await service.list_policies()
