from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, require_admin
from app.services.policy_service import PolicyService
from app.schemas.policy import PolicyResponse, PolicyUpdateRequest
from app.models.user import User

router = APIRouter(prefix="/policies", tags=["Durability & Availability Policies"])


@router.get("", response_model=List[PolicyResponse])
async def list_policies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all configured durability and availability policies."""
    service = PolicyService(db)
    return await service.list_policies()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific storage policy."""
    service = PolicyService(db)
    return await service.get_policy(policy_id)


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: str,
    payload: PolicyUpdateRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only safe policy update with validation."""
    service = PolicyService(db)
    updated = await service.update_policy_safe(policy_id, payload)
    await db.commit()
    return updated
