import uuid
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.core.config import settings
from app.core.redis import is_token_denylisted, RedisUnavailableError
from app.domains.identity.models import User, UserStatus

security = HTTPBearer()
platform_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: access token required",
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        user_id = uuid.UUID(user_id_str)
        jti = payload.get("jti")
        if jti and await is_token_denylisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
    except RedisUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed session revocation service is unavailable; failing closed.",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or user.status == UserStatus.SUSPENDED or user.status == UserStatus.DELETED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is suspended/deleted",
        )

    return user


async def require_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforces that the user has verified their email before sensitive business operations."""
    if not current_user.email_verified or current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address must be verified before performing this operation.",
        )
    return current_user


async def require_platform_admin(
    x_platform_admin_key: Optional[str] = Header(None, alias="X-Platform-Admin-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(platform_security),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """
    Enforces ecosystem-wide Platform Administrator privileges.
    Allows header-based authentication via X-Platform-Admin-Key or token with is_platform_admin claim.
    """
    if x_platform_admin_key:
        expected_key = settings.PLATFORM_ADMIN_KEY or settings.SECRET_KEY
        if secrets.compare_digest(x_platform_admin_key, expected_key):
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid platform administrator key.",
        )

    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.get("type") == "access" and payload.get("is_platform_admin") is True:
                return True
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Platform administrator authorization required (provide valid X-Platform-Admin-Key or admin token).",
    )
