from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.repositories.event_repository import EventRepository
from app.schemas.auth import UserSignupRequest, UserLoginRequest, TokenResponse, UserResponse
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging_config import logger


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.event_repo = EventRepository(session)

    async def signup(self, user_in: UserSignupRequest, role: str = "USER") -> UserResponse:
        existing = await self.user_repo.get_by_email(user_in.email)
        if existing:
            raise ConflictError(message=f"User with email '{user_in.email}' already exists")

        hashed_pw = get_password_hash(user_in.password)
        user = await self.user_repo.create(
            email=user_in.email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=role,
        )
        await self.event_repo.log_event(
            severity="INFO",
            category="AUTH",
            message=f"User registered: {user.email} with role {user.role}",
            details_json={"user_id": user.id, "email": user.email, "role": user.role},
        )
        logger.info(f"User signed up: {user.email} ({user.role})")
        return UserResponse.model_validate(user)

    async def login(self, login_in: UserLoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(login_in.email)
        if not user or not verify_password(login_in.password, user.hashed_password):
            await self.event_repo.log_event(
                severity="WARNING",
                category="AUTH",
                message=f"Failed login attempt for {login_in.email}",
                details_json={"email": login_in.email},
            )
            raise AuthenticationError(message="Invalid email or password")

        if not user.is_active:
            raise AuthenticationError(message="User account is deactivated")

        token = create_access_token(data={"sub": user.id, "role": user.role, "email": user.email})
        await self.event_repo.log_event(
            severity="INFO",
            category="AUTH",
            message=f"User logged in: {user.email}",
            details_json={"user_id": user.id, "email": user.email, "role": user.role},
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None
        return UserResponse.model_validate(user)
