import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Text, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.postgres import Base
import enum


def utcnow():
    return datetime.now(timezone.utc)


class MuscleGroup(str, enum.Enum):
    chest = "chest"
    back = "back"
    shoulders = "shoulders"
    biceps = "biceps"
    triceps = "triceps"
    forearms = "forearms"
    core = "core"
    quads = "quads"
    hamstrings = "hamstrings"
    glutes = "glutes"
    calves = "calves"
    full_body = "full_body"
    cardio = "cardio"


class ExerciseCategory(str, enum.Enum):
    strength = "strength"
    cardio = "cardio"
    flexibility = "flexibility"
    plyometric = "plyometric"
    calisthenics = "calisthenics"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[list | None] = mapped_column(JSON, nullable=True)   # ["Step 1...", "Step 2..."]
    muscle_group: Mapped[MuscleGroup] = mapped_column(SAEnum(MuscleGroup), nullable=False, index=True)
    secondary_muscles: Mapped[list | None] = mapped_column(JSON, nullable=True)
    category: Mapped[ExerciseCategory] = mapped_column(SAEnum(ExerciseCategory), default=ExerciseCategory.strength)
    equipment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)  # beginner/intermediate/advanced
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tips: Mapped[list | None] = mapped_column(JSON, nullable=True)            # Common mistakes / tips
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkoutTemplate(Base):
    """Saved workout templates users can reuse."""
    __tablename__ = "workout_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    exercises: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{"exercise_id": "...", "sets": 3, "reps": "8-12", "rest_seconds": 90}]
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (
        Index("ix_sessions_user_started", "user_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workout_templates.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood_before: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1-5
    mood_after: Mapped[int | None] = mapped_column(Integer, nullable=True)    # 1-5
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_volume_kg: Mapped[float] = mapped_column(Float, default=0.0)
    total_sets: Mapped[int] = mapped_column(Integer, default=0)
    calories_burned: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)  # Snapshot at time of workout
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sets: Mapped[list["WorkoutSet"]] = relationship(
        "WorkoutSet", back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.order_index"
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)         # Position in session
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)          # Set # within same exercise
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Timed sets / planks
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)        # Cardio
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)               # 1-10 rate of exertion
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pr: Mapped[bool] = mapped_column(Boolean, default=False)                   # Marked as personal record
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)

    session: Mapped["WorkoutSession"] = relationship("WorkoutSession", back_populates="sets")


class PersonalRecord(Base):
    """Tracks all-time bests per exercise per user."""
    __tablename__ = "personal_records"
    __table_args__ = (
        Index("ix_pr_user_exercise", "user_id", "exercise_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    max_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_volume_kg: Mapped[float | None] = mapped_column(Float, nullable=True)    # weight × reps
    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workout_sessions.id", ondelete="SET NULL"), nullable=True)
