from typing import AsyncGenerator
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token, UserRole
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.repositories.user_repository import UserRepository
from app.models.user import User


async def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError(message="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AuthenticationError(message="Invalid or expired authentication token")

    user_id = payload["sub"]
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise AuthenticationError(message="User not found")
    if not user.is_active:
        raise AuthenticationError(message="User account is deactivated")

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise PermissionDeniedError(message="Administrative privileges required to access this resource")
    return current_user
