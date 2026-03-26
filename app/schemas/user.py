from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime
from app.models.user import FitnessGoal, ActivityLevel, ExperienceLevel, Gender


class UserOnboardRequest(BaseModel):
    """Called after Firebase login to complete profile setup."""
    full_name: str
    username: str
    gender: Optional[Gender] = None
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    fitness_goal: Optional[FitnessGoal] = None
    activity_level: Optional[ActivityLevel] = None
    experience_level: Optional[ExperienceLevel] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Username must be 3–30 characters")
        return v

    @field_validator("age")
    @classmethod
    def age_valid(cls, v):
        if v is not None and not (10 <= v <= 100):
            raise ValueError("Age must be between 10 and 100")
        return v


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    target_weight_kg: Optional[float] = None
    fitness_goal: Optional[FitnessGoal] = None
    activity_level: Optional[ActivityLevel] = None
    experience_level: Optional[ExperienceLevel] = None
    fcm_token: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    firebase_uid: str
    email: str
    full_name: str
    username: str
    avatar_url: Optional[str]
    bio: Optional[str]
    phone: Optional[str]
    gender: Optional[Gender]
    age: Optional[int]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    target_weight_kg: Optional[float]
    fitness_goal: Optional[FitnessGoal]
    activity_level: Optional[ActivityLevel]
    experience_level: Optional[ExperienceLevel]
    is_premium: bool
    is_profile_complete: bool
    total_workouts: int
    current_streak: int
    longest_streak: int
    total_volume_kg: float
    created_at: datetime
    last_active_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PublicUserResponse(BaseModel):
    """What other users can see."""
    id: str
    username: str
    full_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    fitness_goal: Optional[FitnessGoal]
    total_workouts: int
    current_streak: int
    is_premium: bool

    model_config = {"from_attributes": True}


class TDEEResponse(BaseModel):
    bmr: float
    tdee: float
    goal_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: float
    notes: str
