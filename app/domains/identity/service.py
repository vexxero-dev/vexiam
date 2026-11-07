from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.identity.models import User, UserProfile, UserCredential, UserStatus
from app.domains.identity.schemas import UserRegisterRequest, LoginRequest
from app.core.security import hash_password, verify_password, create_access_token
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

        # Create User
        user = User(
            email=req.email.lower(),
            phone=req.phone,
            status=UserStatus.ACTIVE,  # Defaulting to active for initial developer testing
            email_verified=True,
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
        return user

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

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status.value.lower()}.",
            )

        # Mint Ed25519-signed Access Token
        token = create_access_token(
            subject=str(user.id),
            claims={"email": user.email, "status": user.status.value},
        )
        return user, token
