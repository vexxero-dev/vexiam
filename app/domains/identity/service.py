import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.identity.models import User, UserProfile, UserCredential, UserStatus
from app.domains.identity.schemas import UserRegisterRequest, LoginRequest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_email_verification_token,
    decode_token,
)
from app.core.mailer import send_verification_email
from app.core.config import settings


class IdentityService:
    @staticmethod
    async def register_user(db: AsyncSession, req: UserRegisterRequest) -> User:
        # Check if email exists
        stmt = select(User).where(User.email == req.email.lower())
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists.",
            )

        # Create User with PENDING_VERIFICATION and unverified email
        user = User(
            email=req.email.lower(),
            phone=req.phone,
            status=UserStatus.PENDING_VERIFICATION,
            email_verified=False,
        )
        db.add(user)
        await db.flush()

        # Create Profile
        profile = UserProfile(
            user_id=user.id,
            first_name=req.first_name,
            last_name=req.last_name,
        )
        db.add(profile)

        # Create Credentials
        credential = UserCredential(
            user_id=user.id,
            password_hash=hash_password(req.password),
        )
        db.add(credential)

        await db.commit()
        await db.refresh(user, ["profile"])

        # Send verification email via Resend
        verify_token = create_email_verification_token(str(user.id), user.email)
        send_verification_email(user.email, verify_token, req.first_name)

        return user

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> User:
        try:
            payload = decode_token(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification link is invalid or has expired.",
            )

        if payload.get("type") != "email_verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token type.",
            )

        try:
            user_id = uuid.UUID(payload.get("sub"))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user subject in verification token.",
            )

        stmt = select(User).options(selectinload(User.profile)).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        user.email_verified = True
        user.status = UserStatus.ACTIVE
        await db.commit()
        await db.refresh(user, ["profile"])
        return user

    @staticmethod
    async def resend_verification(db: AsyncSession, email: str) -> bool:
        stmt = select(User).options(selectinload(User.profile)).where(User.email == email.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or user.email_verified:
            return True  # Avoid leaking account state

        verify_token = create_email_verification_token(str(user.id), user.email)
        first_name = user.profile.first_name if user.profile else None
        send_verification_email(user.email, verify_token, first_name)
        return True

    @staticmethod
    async def authenticate_user(db: AsyncSession, req: LoginRequest) -> tuple[User, str]:
        stmt = (
            select(User)
            .options(selectinload(User.credentials), selectinload(User.profile))
            .where(User.email == req.email.lower())
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not verify_password(req.password, user.credentials.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if user.status == UserStatus.SUSPENDED or user.status == UserStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status.value.lower()}.",
            )

        # Mint Ed25519-signed Access Token
        token = create_access_token(
            subject=str(user.id),
            claims={"email": user.email, "status": user.status.value, "email_verified": user.email_verified},
        )
        return user, token
