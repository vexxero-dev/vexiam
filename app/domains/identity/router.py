from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import security
from app.domains.identity.schemas import (
    UserRegisterRequest,
    UserResponse,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
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
    summary="Authenticate and obtain an Ed25519-signed JWT and Refresh Token",
)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user, access_token, refresh_token = await IdentityService.authenticate_user(db, req)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue a fresh access token",
)
async def refresh_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    user, new_access, new_refresh = await IdentityService.refresh_access_token(db, req.refresh_token)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke current access token and optional refresh token via Redis",
)
async def logout(
    req: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    await IdentityService.logout(
        credentials.credentials,
        req.refresh_token if req else None,
    )
    return {"message": "Logged out successfully. Tokens have been revoked."}


@router.post(
    "/verify-email",
    response_model=UserResponse,
    summary="Verify user email address using signed token",
)
async def verify_email(
    req: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    return await IdentityService.verify_email(db, req.token)


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Resend verification email to user",
)
async def resend_verification(
    req: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.resend_verification(db, req.email)
    return {"message": "If the email is unverified, a new link has been sent."}
