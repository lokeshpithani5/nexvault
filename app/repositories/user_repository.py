from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, email: str, hashed_password: str, full_name: Optional[str] = None, role: str = "USER") -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def list_all(self) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
