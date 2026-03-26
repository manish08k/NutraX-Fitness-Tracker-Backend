from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.workout import (
    ExerciseCreate, ExerciseResponse,
    WorkoutSessionCreate, WorkoutSessionUpdate, WorkoutSessionResponse,
    TemplateCreate, TemplateResponse,
    WorkoutStatsResponse, PersonalRecordResponse,
)
from app.services.workout_service import WorkoutService

router = APIRouter()


# ── Exercise Library ──────────────────────────────────────────────
@router.get("/exercises", response_model=List[ExerciseResponse])
async def list_exercises(
    muscle_group: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.list_exercises(muscle_group, category, search, equipment)


@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(exercise_id: str, db: AsyncSession = Depends(get_db)):
    service = WorkoutService(db)
    ex = await service.get_exercise(exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ex


@router.post("/exercises", response_model=ExerciseResponse, status_code=201)
async def create_custom_exercise(
    payload: ExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.create_exercise(payload, current_user.id)


# ── Templates ─────────────────────────────────────────────────────
@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.list_templates(current_user.id)


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    payload: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.create_template(payload, current_user.id)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    await service.delete_template(template_id, current_user.id)


# ── Workout Sessions ──────────────────────────────────────────────
@router.post("/sessions", response_model=WorkoutSessionResponse, status_code=201)
async def log_workout(
    payload: WorkoutSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.create_session(payload, current_user)


@router.get("/sessions", response_model=List[WorkoutSessionResponse])
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.list_sessions(current_user.id, limit, offset)


@router.get("/sessions/{session_id}", response_model=WorkoutSessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    session = await service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Workout session not found")
    return session


@router.patch("/sessions/{session_id}", response_model=WorkoutSessionResponse)
async def update_session(
    session_id: str,
    payload: WorkoutSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.update_session(session_id, payload, current_user.id)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    await service.delete_session(session_id, current_user.id)


# ── Stats & PRs ───────────────────────────────────────────────────
@router.get("/stats", response_model=WorkoutStatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.get_stats(current_user)


@router.get("/personal-records", response_model=List[PersonalRecordResponse])
async def get_personal_records(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutService(db)
    return await service.get_personal_records(current_user.id)
