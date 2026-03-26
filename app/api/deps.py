from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.postgres import get_db
from app.db.redis import (
    get_user_session, store_user_session,
    is_blacklisted, rate_limit_check
)
from app.core.security import verify_firebase_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates Firebase ID token on every request.
    Uses Redis session cache to avoid hitting Firebase on every call.
    """
    id_token = credentials.credentials

    # Verify Firebase token → get UID
    claims = verify_firebase_token(id_token)
    uid = claims["uid"]

    # Check blacklist (revoked users)
    if await is_blacklisted(uid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been suspended. Please contact support.",
        )

    # Try Redis session cache first (avoids DB hit)
    cached = await get_user_session(uid)
    if cached:
        # Reconstruct minimal User object from cache
        user_id = cached.get("id")
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user

    # Not cached → fetch from DB by Firebase UID
    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please complete registration.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    # Cache session for 1 hour
    await store_user_session(uid, {"id": user.id}, ttl=3600)
    return user


async def get_premium_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a GymBrain Premium subscription.",
        )
    return current_user


async def rate_limit(
    request: Request,
    limit: int = 60,
    window: int = 60,
) -> None:
    """General rate limiter — 60 requests/min per IP by default."""
    ip = request.client.host
    key = f"rl:{ip}:{request.url.path}"
    allowed, remaining = await rate_limit_check(key, limit, window)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down.",
            headers={"Retry-After": str(window)},
        )
