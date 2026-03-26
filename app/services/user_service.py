import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.user import User
from app.schemas.user import UserOnboardRequest, UserUpdateRequest
from app.db.redis import invalidate_user_session
from app.core.logger import logger


def utcnow():
    return datetime.now(timezone.utc)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_uid(self, firebase_uid: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_or_complete_user(
        self,
        firebase_uid: str,
        email: str,
        avatar_url: str | None,
        profile: UserOnboardRequest,
        existing_user: User | None = None,
    ) -> User:
        # Check username is unique
        taken = await self.get_by_username(profile.username)
        if taken and (not existing_user or taken.id != existing_user.id):
            raise HTTPException(status_code=409, detail="Username already taken")

        if existing_user:
            user = existing_user
        else:
            user = User(
                id=str(uuid.uuid4()),
                firebase_uid=firebase_uid,
                email=email,
                avatar_url=avatar_url,
            )
            self.db.add(user)

        # Apply profile fields
        user.full_name = profile.full_name
        user.username = profile.username.lower()
        if profile.gender is not None:
            user.gender = profile.gender
        if profile.age is not None:
            user.age = profile.age
        if profile.weight_kg is not None:
            user.weight_kg = profile.weight_kg
        if profile.height_cm is not None:
            user.height_cm = profile.height_cm
        if profile.fitness_goal is not None:
            user.fitness_goal = profile.fitness_goal
        if profile.activity_level is not None:
            user.activity_level = profile.activity_level
        if profile.experience_level is not None:
            user.experience_level = profile.experience_level

        user.is_profile_complete = True
        user.updated_at = utcnow()

        await self.db.flush()
        await self.db.refresh(user)

        # Trigger welcome notification async (non-blocking)
        try:
            from app.tasks.tasks import send_welcome_notification
            send_welcome_notification.delay(user.id, user.full_name, user.email)
        except Exception:
            pass  # Celery not critical on registration

        logger.info(f"User onboarded: {user.username} ({user.id})")
        return user

    async def update_user(self, user: User, payload: UserUpdateRequest) -> User:
        update_data = payload.model_dump(exclude_none=True)

        # If username changed, check uniqueness
        if "username" in update_data:
            new_username = update_data["username"].lower()
            taken = await self.get_by_username(new_username)
            if taken and taken.id != user.id:
                raise HTTPException(status_code=409, detail="Username already taken")
            update_data["username"] = new_username

        for field, value in update_data.items():
            setattr(user, field, value)

        # Mark profile complete if key fields present
        if all([user.age, user.weight_kg, user.height_cm, user.fitness_goal]):
            user.is_profile_complete = True

        user.updated_at = utcnow()
        await self.db.flush()
        await self.db.refresh(user)

        # Invalidate Redis session so next request fetches fresh data
        await invalidate_user_session(user.firebase_uid)

        return user

    async def soft_delete(self, user: User) -> None:
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.gymbrain"
        user.updated_at = utcnow()
        await self.db.flush()
        await invalidate_user_session(user.firebase_uid)
        logger.info(f"User soft-deleted: {user.id}")

    async def update_last_active(self, user: User) -> None:
        user.last_active_at = utcnow()
        await self.db.flush()
