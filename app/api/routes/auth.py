from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user, rate_limit
from app.core.security import verify_firebase_token
from app.db.redis import invalidate_user_session, blacklist_token
from app.models.user import User
from app.schemas.user import UserOnboardRequest, UserProfileResponse
from app.services.user_service import UserService

router = APIRouter()


@router.post("/verify", response_model=dict)
async def verify_token(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """
    Step 1 of auth flow:
    Flutter app sends Firebase ID token → backend verifies it.
    Returns whether user exists (needs onboarding) or is ready.
    """
    id_token = body.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="id_token is required")

    claims = verify_firebase_token(id_token)
    uid = claims["uid"]

    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalar_one_or_none()

    if user and user.is_profile_complete:
        return {
            "status": "existing_user",
            "user_id": user.id,
            "username": user.username,
            "is_premium": user.is_premium,
        }
    elif user:
        return {"status": "incomplete_profile", "user_id": user.id}
    else:
        return {
            "status": "new_user",
            "email": claims.get("email", ""),
            "name": claims.get("name", ""),
            "avatar_url": claims.get("picture", ""),
        }


@router.post("/onboard", response_model=UserProfileResponse, status_code=201)
async def onboard_user(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2 of auth flow (new users only):
    Creates the user record in PostgreSQL after Firebase auth.
    Requires Firebase ID token + profile data.
    """
    id_token = body.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="id_token is required")

    claims = verify_firebase_token(id_token)
    uid = claims["uid"]

    # Check if already exists
    result = await db.execute(select(User).where(User.firebase_uid == uid))
    existing = result.scalar_one_or_none()
    if existing and existing.is_profile_complete:
        raise HTTPException(status_code=409, detail="User already registered")

    try:
        profile_data = UserOnboardRequest(**{k: v for k, v in body.items() if k != "id_token"})
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    service = UserService(db)
    user = await service.create_or_complete_user(
        firebase_uid=uid,
        email=claims.get("email", ""),
        avatar_url=claims.get("picture"),
        profile=profile_data,
        existing_user=existing,
    )
    return UserProfileResponse.model_validate(user)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Invalidate session cache (doesn't revoke Firebase token — that's on client side)."""
    await invalidate_user_session(current_user.firebase_uid)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Fast profile fetch using cached session."""
    return UserProfileResponse.model_validate(current_user)
