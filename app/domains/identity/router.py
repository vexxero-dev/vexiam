from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.domains.identity.schemas import (
    UserRegisterRequest,
    UserResponse,
    LoginRequest,
    TokenResponse,
)
from app.domains.identity.service import IdentityService

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new individual VEX IAM account",
)
async def register(
    req: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    return await IdentityService.register_user(db, req)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain an Ed25519-signed JWT",
)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user, token = await IdentityService.authenticate_user(db, req)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )
