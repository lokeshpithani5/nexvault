from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth import UserSignupRequest, UserLoginRequest, TokenResponse, UserResponse
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserSignupRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    user = await auth_service.signup(user_in, role="USER")
    await db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(login_in: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    token_resp = await auth_service.login(login_in)
    await db.commit()
    return token_resp


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # In stateless JWT architectures, logout invalidates client-side tokens
    return {"message": f"Successfully logged out {current_user.email}"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
