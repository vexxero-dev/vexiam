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
    create_refresh_token,
    create_email_verification_token,
    decode_token,
)
from app.core.mailer import send_verification_email
from app.core.config import settings
from app.core.redis import denylist_token, is_token_denylisted


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

        # Mint Ed25519-signed Access Token and single-use Refresh Token
        claims = {"email": user.email, "status": user.status.value, "email_verified": user.email_verified}
        access_token = create_access_token(subject=str(user.id), claims=claims)
        refresh_token = create_refresh_token(subject=str(user.id), claims=claims)
        return user, access_token, refresh_token

    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token_str: str) -> tuple[User, str, str]:
        """
        Validates refresh token, checks revocation, invalidates old refresh token (rotation),
        and returns fresh access and refresh tokens.
        """
        try:
            payload = decode_token(refresh_token_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or expired.",
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token.",
            )

        jti = payload.get("jti")
        if jti and await is_token_denylisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or already consumed.",
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject.",
            )

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user identifier.",
            )

        stmt = select(User).options(selectinload(User.profile)).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or user.status == UserStatus.SUSPENDED or user.status == UserStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or account is suspended/deleted.",
            )

        # Single-use rotation: Invalidate old refresh token
        if jti:
            await denylist_token(jti, expire_seconds=86400 * settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Mint rotated tokens
        claims = {"email": user.email, "status": user.status.value, "email_verified": user.email_verified}
        new_access_token = create_access_token(subject=str(user.id), claims=claims)
        new_refresh_token = create_refresh_token(subject=str(user.id), claims=claims)

        return user, new_access_token, new_refresh_token

    @staticmethod
    async def logout(access_token_str: str, refresh_token_str: str | None = None) -> None:
        """Denylists current access token and optional refresh token in Redis."""
        try:
            payload = decode_token(access_token_str)
            jti = payload.get("jti")
            if jti:
                await denylist_token(jti, expire_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        except Exception:
            pass

        if refresh_token_str:
            try:
                ref_payload = decode_token(refresh_token_str)
                ref_jti = ref_payload.get("jti")
                if ref_jti:
                    await denylist_token(ref_jti, expire_seconds=86400 * settings.REFRESH_TOKEN_EXPIRE_DAYS)
            except Exception:
                pass
