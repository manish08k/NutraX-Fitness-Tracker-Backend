import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Float, Integer, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base
import enum


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class FitnessGoal(str, enum.Enum):
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"
    endurance = "endurance"
    flexibility = "flexibility"
    maintenance = "maintenance"
    athletic_performance = "athletic_performance"


class ActivityLevel(str, enum.Enum):
    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    extra_active = "extra_active"


class ExperienceLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Fitness Profile ───────────────────────────────────────────
    gender: Mapped[Gender | None] = mapped_column(SAEnum(Gender), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    fitness_goal: Mapped[FitnessGoal | None] = mapped_column(SAEnum(FitnessGoal), nullable=True)
    activity_level: Mapped[ActivityLevel | None] = mapped_column(SAEnum(ActivityLevel), nullable=True)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(SAEnum(ExperienceLevel), nullable=True)

    # ── Account Status ────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_profile_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    premium_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Push notification token

    # ── Stats (denormalized for fast reads) ───────────────────────
    total_workouts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_volume_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
