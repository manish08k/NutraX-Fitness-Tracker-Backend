import uuid
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, distinct
from fastapi import HTTPException
from typing import Optional
from collections import defaultdict

from app.models.workout import (
    Exercise, WorkoutSession, WorkoutSet,
    WorkoutTemplate, PersonalRecord, MuscleGroup
)
from app.schemas.workout import (
    ExerciseCreate, WorkoutSessionCreate, WorkoutSessionUpdate,
    TemplateCreate, WorkoutStatsResponse, PersonalRecordResponse
)
from app.db.redis import cache_get, cache_set, cache_delete, cache_delete_pattern, increment_workout_count
from app.core.logger import logger


def utcnow():
    return datetime.now(timezone.utc)


class WorkoutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Exercises ─────────────────────────────────────────────────
    async def list_exercises(
        self,
        muscle_group: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        equipment: Optional[str] = None,
    ) -> list[Exercise]:
        cache_key = f"exercises:{muscle_group}:{category}:{search}:{equipment}"
        cached = await cache_get(cache_key)
        if cached:
            return [Exercise(**e) for e in cached] if isinstance(cached[0], dict) else cached

        query = select(Exercise)
        if muscle_group:
            query = query.where(Exercise.muscle_group == muscle_group)
        if category:
            query = query.where(Exercise.category == category)
        if search:
            query = query.where(Exercise.name.ilike(f"%{search}%"))
        if equipment:
            query = query.where(Exercise.equipment.ilike(f"%{equipment}%"))

        result = await self.db.execute(query.order_by(Exercise.name).limit(100))
        exercises = list(result.scalars().all())

        # Cache 1 hour
        await cache_set(cache_key, [
            {c.name: getattr(e, c.name) for c in Exercise.__table__.columns}
            for e in exercises
        ], ttl=3600)
        return exercises

    async def get_exercise(self, exercise_id: str) -> Optional[Exercise]:
        result = await self.db.execute(
            select(Exercise).where(Exercise.id == exercise_id)
        )
        return result.scalar_one_or_none()

    async def create_exercise(self, payload: ExerciseCreate, user_id: str) -> Exercise:
        ex = Exercise(
            id=str(uuid.uuid4()),
            **payload.model_dump(),
            is_custom=True,
            created_by=user_id,
        )
        self.db.add(ex)
        await self.db.flush()
        await cache_delete_pattern("exercises:*")
        return ex

    # ── Templates ─────────────────────────────────────────────────
    async def list_templates(self, user_id: str) -> list[WorkoutTemplate]:
        result = await self.db.execute(
            select(WorkoutTemplate).where(WorkoutTemplate.user_id == user_id)
            .order_by(desc(WorkoutTemplate.updated_at))
        )
        return list(result.scalars().all())

    async def create_template(self, payload: TemplateCreate, user_id: str) -> WorkoutTemplate:
        t = WorkoutTemplate(
            id=str(uuid.uuid4()),
            user_id=user_id,
            **payload.model_dump(),
        )
        self.db.add(t)
        await self.db.flush()
        return t

    async def delete_template(self, template_id: str, user_id: str) -> None:
        result = await self.db.execute(
            select(WorkoutTemplate).where(
                WorkoutTemplate.id == template_id,
                WorkoutTemplate.user_id == user_id,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Template not found")
        await self.db.delete(t)

    # ── Sessions ──────────────────────────────────────────────────
    async def create_session(self, payload: WorkoutSessionCreate, user) -> WorkoutSession:
        session = WorkoutSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            template_id=payload.template_id,
            name=payload.name,
            notes=payload.notes,
            mood_before=payload.mood_before,
            body_weight_kg=payload.body_weight_kg,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
        )

        if payload.started_at and payload.ended_at:
            session.duration_seconds = int(
                (payload.ended_at - payload.started_at).total_seconds()
            )

        self.db.add(session)
        await self.db.flush()

        total_volume = 0.0
        total_sets = 0
        pr_exercise_ids = []

        for set_data in payload.sets:
            ws = WorkoutSet(
                id=str(uuid.uuid4()),
                session_id=session.id,
                **set_data.model_dump(),
            )
            self.db.add(ws)
            total_sets += 1
            if set_data.weight_kg and set_data.reps and not set_data.is_warmup:
                total_volume += set_data.weight_kg * set_data.reps

            # Check for personal record
            if set_data.weight_kg and set_data.reps:
                is_pr = await self._check_and_update_pr(
                    user.id, set_data.exercise_id,
                    set_data.weight_kg, set_data.reps,
                    set_data.weight_kg * set_data.reps, session.id
                )
                if is_pr:
                    ws.is_pr = True
                    pr_exercise_ids.append(set_data.exercise_id)

        session.total_volume_kg = round(total_volume, 2)
        session.total_sets = total_sets
        await self.db.flush()

        # Update user denormalized stats
        user.total_workouts = (user.total_workouts or 0) + 1
        user.total_volume_kg = round((user.total_volume_kg or 0) + total_volume, 2)
        await self._update_streak(user, payload.started_at)
        await self.db.flush()

        # Invalidate caches
        await cache_delete_pattern(f"sessions:{user.id}:*")
        await cache_delete(f"stats:{user.id}")

        # Trigger background analytics
        try:
            from app.tasks.tasks import post_workout_analytics
            post_workout_analytics.delay(user.id, session.id, pr_exercise_ids)
        except Exception:
            pass

        await self.db.refresh(session, ["sets"])
        return session

    async def _check_and_update_pr(
        self,
        user_id: str,
        exercise_id: str,
        weight_kg: float,
        reps: int,
        volume_kg: float,
        session_id: str,
    ) -> bool:
        result = await self.db.execute(
            select(PersonalRecord).where(
                PersonalRecord.user_id == user_id,
                PersonalRecord.exercise_id == exercise_id,
            )
        )
        pr = result.scalar_one_or_none()
        is_new_pr = False

        if not pr:
            pr = PersonalRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                exercise_id=exercise_id,
                max_weight_kg=weight_kg,
                max_reps=reps,
                max_volume_kg=volume_kg,
                session_id=session_id,
                achieved_at=utcnow(),
            )
            self.db.add(pr)
            is_new_pr = True
        else:
            if weight_kg > (pr.max_weight_kg or 0):
                pr.max_weight_kg = weight_kg
                pr.achieved_at = utcnow()
                pr.session_id = session_id
                is_new_pr = True
            if volume_kg > (pr.max_volume_kg or 0):
                pr.max_volume_kg = volume_kg
                is_new_pr = True
            if reps > (pr.max_reps or 0):
                pr.max_reps = reps
                is_new_pr = True

        await self.db.flush()
        return is_new_pr

    async def _update_streak(self, user, workout_date: datetime) -> None:
        """Update current and longest streak."""
        workout_day = workout_date.date() if hasattr(workout_date, 'date') else workout_date
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        if workout_day == today or workout_day == yesterday:
            user.current_streak = (user.current_streak or 0) + 1
            if user.current_streak > (user.longest_streak or 0):
                user.longest_streak = user.current_streak
        else:
            user.current_streak = 1

    async def list_sessions(self, user_id: str, limit: int, offset: int) -> list[WorkoutSession]:
        result = await self.db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .order_by(desc(WorkoutSession.started_at))
            .limit(limit)
            .offset(offset)
        )
        sessions = list(result.scalars().all())
        # Load sets for each
        for s in sessions:
            await self.db.refresh(s, ["sets"])
        return sessions

    async def get_session(self, session_id: str, user_id: str) -> Optional[WorkoutSession]:
        result = await self.db.execute(
            select(WorkoutSession).where(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
        )
        s = result.scalar_one_or_none()
        if s:
            await self.db.refresh(s, ["sets"])
        return s

    async def update_session(self, session_id: str, payload: WorkoutSessionUpdate, user_id: str) -> WorkoutSession:
        s = await self.get_session(session_id, user_id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(s, field, value)
        await self.db.flush()
        await cache_delete(f"stats:{user_id}")
        return s

    async def delete_session(self, session_id: str, user_id: str) -> None:
        s = await self.get_session(session_id, user_id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        await self.db.delete(s)
        await cache_delete_pattern(f"sessions:{user_id}:*")
        await cache_delete(f"stats:{user_id}")

    # ── Stats ─────────────────────────────────────────────────────
    async def get_stats(self, user) -> WorkoutStatsResponse:
        cache_key = f"stats:{user.id}"
        cached = await cache_get(cache_key)
        if cached:
            return WorkoutStatsResponse(**cached)

        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Aggregate from DB
        agg = await self.db.execute(
            select(
                func.count(WorkoutSession.id).label("total"),
                func.coalesce(func.sum(WorkoutSession.total_volume_kg), 0).label("volume"),
                func.coalesce(func.sum(WorkoutSession.duration_seconds), 0).label("duration"),
                func.coalesce(func.sum(WorkoutSession.total_sets), 0).label("sets"),
            ).where(WorkoutSession.user_id == user.id)
        )
        row = agg.one()

        # This week
        week_res = await self.db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id == user.id,
                func.date(WorkoutSession.started_at) >= week_start,
            )
        )
        this_week = week_res.scalar() or 0

        # This month
        month_res = await self.db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id == user.id,
                func.date(WorkoutSession.started_at) >= month_start,
            )
        )
        this_month = month_res.scalar() or 0

        # Most trained muscle group
        muscle_res = await self.db.execute(
            select(Exercise.muscle_group, func.count(WorkoutSet.id).label("cnt"))
            .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.id)
            .join(WorkoutSession, WorkoutSession.id == WorkoutSet.session_id)
            .where(WorkoutSession.user_id == user.id)
            .group_by(Exercise.muscle_group)
            .order_by(desc("cnt"))
            .limit(1)
        )
        top_muscle_row = muscle_res.first()
        top_muscle = top_muscle_row[0].value if top_muscle_row else None

        # PRs
        prs = await self.get_personal_records(user.id)

        total = int(row.total)
        duration_min = int(row.duration) // 60

        stats = WorkoutStatsResponse(
            total_sessions=total,
            total_volume_kg=float(row.volume),
            total_duration_minutes=duration_min,
            avg_session_duration_minutes=round(duration_min / total, 1) if total > 0 else 0,
            total_sets=int(row.sets),
            current_streak=user.current_streak or 0,
            longest_streak=user.longest_streak or 0,
            most_trained_muscle=top_muscle,
            this_week_sessions=this_week,
            this_month_sessions=this_month,
            personal_records=prs,
        )

        await cache_set(cache_key, stats.model_dump(mode="json"), ttl=300)
        return stats

    async def get_personal_records(self, user_id: str) -> list[PersonalRecordResponse]:
        result = await self.db.execute(
            select(PersonalRecord, Exercise.name)
            .join(Exercise, Exercise.id == PersonalRecord.exercise_id)
            .where(PersonalRecord.user_id == user_id)
            .order_by(desc(PersonalRecord.achieved_at))
        )
        rows = result.all()
        return [
            PersonalRecordResponse(
                exercise_id=pr.exercise_id,
                exercise_name=name,
                max_weight_kg=pr.max_weight_kg,
                max_reps=pr.max_reps,
                max_volume_kg=pr.max_volume_kg,
                achieved_at=pr.achieved_at,
            )
            for pr, name in rows
        ]
