import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisUnavailableError(RuntimeError):
    """Raised when Redis is required in production but unavailable."""
    pass


# In-memory fallback store when Redis is unavailable in non-production (e.g. SQLite test runs)
_memory_denylist: set[str] = set()
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None and settings.REDIS_URL:
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.5,
            )
            await client.ping()
            _redis_client = client
        except Exception:
            _redis_client = None
    return _redis_client


async def denylist_token(jti: str, expire_seconds: int = 86400) -> None:
    """Adds a token's JTI to the revocation denylist. Fails closed in production if Redis is down."""
    if not jti:
        return
    r = await get_redis()
    if r:
        try:
            await r.setex(f"denylist:{jti}", expire_seconds, "revoked")
            return
        except Exception as exc:
            logger.error(f"Redis denylist write failed: {exc}")
            if settings.ENVIRONMENT == "production":
                raise RedisUnavailableError(f"Distributed session revocation write failed: {exc}")
    elif settings.ENVIRONMENT == "production":
        raise RedisUnavailableError("Distributed session store is unavailable in production; refusing in-memory fallback.")

    _memory_denylist.add(jti)


async def is_token_denylisted(jti: str) -> bool:
    """Checks whether a token's JTI has been revoked. Fails closed in production if Redis is down."""
    if not jti:
        return False
    if jti in _memory_denylist:
        return True
    r = await get_redis()
    if r:
        try:
            val = await r.get(f"denylist:{jti}")
            return val is not None
        except Exception as exc:
            logger.error(f"Redis denylist read failed: {exc}")
            if settings.ENVIRONMENT == "production":
                raise RedisUnavailableError("Redis distributed store unavailable in production.")
    elif settings.ENVIRONMENT == "production":
        raise RedisUnavailableError("Redis distributed store unavailable in production.")
    return False
