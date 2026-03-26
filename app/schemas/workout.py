from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.workout import MuscleGroup, ExerciseCategory


# ── Exercises ─────────────────────────────────────────────────────
class ExerciseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: Optional[List[str]] = None
    muscle_group: MuscleGroup
    secondary_muscles: Optional[List[str]] = None
    category: ExerciseCategory = ExerciseCategory.strength
    equipment: Optional[str] = None
    difficulty: Optional[str] = None
    tips: Optional[List[str]] = None


class ExerciseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    instructions: Optional[List[str]]
    muscle_group: MuscleGroup
    secondary_muscles: Optional[List[str]]
    category: ExerciseCategory
    equipment: Optional[str]
    difficulty: Optional[str]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    tips: Optional[List[str]]
    is_custom: bool
    model_config = {"from_attributes": True}


# ── Sets ──────────────────────────────────────────────────────────
class SetCreate(BaseModel):
    exercise_id: str
    order_index: int
    set_number: int
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    duration_seconds: Optional[int] = None
    distance_m: Optional[float] = None
    rpe: Optional[float] = None
    is_warmup: bool = False
    notes: Optional[str] = None

    @field_validator("rpe")
    @classmethod
    def rpe_range(cls, v):
        if v is not None and not (1 <= v <= 10):
            raise ValueError("RPE must be between 1 and 10")
        return v


class SetResponse(SetCreate):
    id: str
    session_id: str
    is_pr: bool
    model_config = {"from_attributes": True}


# ── Workout Session ───────────────────────────────────────────────
class WorkoutSessionCreate(BaseModel):
    name: str
    template_id: Optional[str] = None
    notes: Optional[str] = None
    mood_before: Optional[int] = None
    body_weight_kg: Optional[float] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    sets: List[SetCreate] = []


class WorkoutSessionUpdate(BaseModel):
    notes: Optional[str] = None
    mood_after: Optional[int] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    calories_burned: Optional[float] = None


class WorkoutSessionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    notes: Optional[str]
    mood_before: Optional[int]
    mood_after: Optional[int]
    duration_seconds: Optional[int]
    total_volume_kg: float
    total_sets: int
    calories_burned: Optional[float]
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime
    sets: List[SetResponse] = []
    model_config = {"from_attributes": True}


# ── Template ─────────────────────────────────────────────────────
class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    exercises: List[dict]
    estimated_duration_minutes: Optional[int] = None
    is_public: bool = False


class TemplateResponse(TemplateCreate):
    id: str
    user_id: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Stats ─────────────────────────────────────────────────────────
class PersonalRecordResponse(BaseModel):
    exercise_id: str
    exercise_name: str
    max_weight_kg: Optional[float]
    max_reps: Optional[int]
    max_volume_kg: Optional[float]
    achieved_at: datetime
    model_config = {"from_attributes": True}


class WorkoutStatsResponse(BaseModel):
    total_sessions: int
    total_volume_kg: float
    total_duration_minutes: int
    avg_session_duration_minutes: float
    total_sets: int
    current_streak: int
    longest_streak: int
    most_trained_muscle: Optional[str]
    this_week_sessions: int
    this_month_sessions: int
    personal_records: List[PersonalRecordResponse]
