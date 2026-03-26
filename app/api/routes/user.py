from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserUpdateRequest, PublicUserResponse, TDEEResponse
from app.services.user_service import UserService
from app.utils.helpers import calculate_tdee_full

router = APIRouter()


@router.get("/profile", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return UserProfileResponse.model_validate(current_user)


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    updated = await service.update_user(current_user, payload)
    return UserProfileResponse.model_validate(updated)


@router.get("/profile/{username}", response_model=PublicUserResponse)
async def get_public_profile(username: str, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    user = await service.get_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return PublicUserResponse.model_validate(user)


@router.get("/tdee", response_model=TDEEResponse)
async def get_my_tdee(current_user: User = Depends(get_current_user)):
    """Calculate personalised TDEE and recommended macros."""
    if not all([current_user.age, current_user.weight_kg, current_user.height_cm]):
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile (age, weight, height) to calculate TDEE.",
        )
    return calculate_tdee_full(
        age=current_user.age,
        weight_kg=current_user.weight_kg,
        height_cm=current_user.height_cm,
        gender=current_user.gender.value if current_user.gender else "male",
        activity_level=current_user.activity_level.value if current_user.activity_level else "sedentary",
        goal=current_user.fitness_goal.value if current_user.fitness_goal else "maintenance",
    )


@router.delete("/account", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    await service.soft_delete(current_user)
