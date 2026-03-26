import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logger import logger

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create Redis connection (Upstash TLS)."""
    global _redis
    if _redis is None:
        # Upstash provides a rediss:// TLS URL — works directly
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        logger.info("✅ Redis connected (Upstash)")
    return _redis


async def ping_redis() -> bool:
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ── Generic Cache ─────────────────────────────────────────────────
async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl)


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    data = await r.get(key)
    return json.loads(data) if data else None


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def cache_delete_pattern(pattern: str) -> None:
    r = await get_redis()
    keys = await r.keys(pattern)
    if keys:
        await r.delete(*keys)


# ── Rate Limiting ─────────────────────────────────────────────────
async def rate_limit_check(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """
    Sliding window rate limiter.
    Returns (allowed: bool, remaining: int)
    """
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    count = results[0]
    remaining = max(0, limit - count)
    return count <= limit, remaining


# ── Session / Token Blacklist ─────────────────────────────────────
async def blacklist_token(uid: str, ttl: int = 3600) -> None:
    """Blacklist a Firebase UID (force re-login)."""
    r = await get_redis()
    await r.set(f"blacklist:{uid}", "1", ex=ttl)


async def is_blacklisted(uid: str) -> bool:
    r = await get_redis()
    return bool(await r.get(f"blacklist:{uid}"))


# ── User Session Store ────────────────────────────────────────────
async def store_user_session(uid: str, user_data: dict, ttl: int = 86400) -> None:
    """Cache user profile for fast auth lookups."""
    await cache_set(f"session:{uid}", user_data, ttl)


async def get_user_session(uid: str) -> Optional[dict]:
    return await cache_get(f"session:{uid}")


async def invalidate_user_session(uid: str) -> None:
    await cache_delete(f"session:{uid}")


# ── Leaderboard / Streak Helpers ──────────────────────────────────
async def increment_workout_count(uid: str) -> int:
    r = await get_redis()
    key = f"wcount:{uid}"
    count = await r.incr(key)
    await r.expire(key, 86400 * 365)
    return count


async def get_workout_count(uid: str) -> int:
    r = await get_redis()
    val = await r.get(f"wcount:{uid}")
    return int(val) if val else 0
