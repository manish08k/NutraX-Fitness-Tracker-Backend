import uuid
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from typing import Optional
from collections import defaultdict

from app.models.diet import FoodItem, DietLog, NutritionGoal, WaterLog
from app.schemas.diet import (
    FoodItemCreate, DietLogCreate, DailyNutritionSummary,
    NutritionGoalCreate, WaterLogCreate, MealGroup,
    DietLogResponse, NutritionWeekSummary
)
from app.db.redis import cache_get, cache_set, cache_delete


def utcnow():
    return datetime.now(timezone.utc)


class DietService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Foods ─────────────────────────────────────────────────────
    async def search_foods(self, query: str, limit: int = 20) -> list[FoodItem]:
        cache_key = f"foods:{query.lower()}:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        result = await self.db.execute(
            select(FoodItem)
            .where(FoodItem.name.ilike(f"%{query}%"))
            .order_by(FoodItem.is_verified.desc(), FoodItem.name)
            .limit(limit)
        )
        foods = list(result.scalars().all())
        await cache_set(cache_key, [
            {c.name: getattr(f, c.name) for c in FoodItem.__table__.columns}
            for f in foods
        ], ttl=1800)
        return foods

    async def get_by_barcode(self, barcode: str) -> Optional[FoodItem]:
        result = await self.db.execute(
            select(FoodItem).where(FoodItem.barcode == barcode)
        )
        return result.scalar_one_or_none()

    async def create_food(self, payload: FoodItemCreate, user_id: str) -> FoodItem:
        food = FoodItem(
            id=str(uuid.uuid4()),
            **payload.model_dump(),
            is_custom=True,
            created_by=user_id,
        )
        self.db.add(food)
        await self.db.flush()
        return food

    async def _get_food_or_404(self, food_id: str) -> FoodItem:
        result = await self.db.execute(
            select(FoodItem).where(FoodItem.id == food_id)
        )
        food = result.scalar_one_or_none()
        if not food:
            raise HTTPException(status_code=404, detail="Food item not found")
        return food

    # ── Logs ──────────────────────────────────────────────────────
    async def log_meal(self, payload: DietLogCreate, user_id: str) -> DietLog:
        food = await self._get_food_or_404(payload.food_item_id)
        ratio = payload.quantity_g / 100.0

        log = DietLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            log_date=payload.log_date,
            meal_type=payload.meal_type,
            food_item_id=payload.food_item_id,
            food_name=food.name,  # snapshot
            quantity_g=payload.quantity_g,
            calories=round(food.calories_per_100g * ratio, 1),
            protein_g=round(food.protein_per_100g * ratio, 1),
            carbs_g=round(food.carbs_per_100g * ratio, 1),
            fat_g=round(food.fat_per_100g * ratio, 1),
            fiber_g=round(food.fiber_per_100g * ratio, 1),
        )
        self.db.add(log)
        await self.db.flush()

        # Invalidate daily cache
        await cache_delete(f"diet:{user_id}:{payload.log_date}")
        return log

    async def delete_log(self, log_id: str, user_id: str) -> None:
        result = await self.db.execute(
            select(DietLog).where(DietLog.id == log_id, DietLog.user_id == user_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        log_date = log.log_date
        await self.db.delete(log)
        await cache_delete(f"diet:{user_id}:{log_date}")

    async def get_daily_summary(self, user_id: str, log_date: date) -> DailyNutritionSummary:
        cache_key = f"diet:{user_id}:{log_date}"
        cached = await cache_get(cache_key)
        if cached:
            return DailyNutritionSummary(**cached)

        # Fetch all logs for the day
        result = await self.db.execute(
            select(DietLog)
            .where(DietLog.user_id == user_id, DietLog.log_date == log_date)
            .order_by(DietLog.logged_at)
        )
        logs = list(result.scalars().all())

        # Water for the day
        water_total = await self.get_water_total(user_id, log_date)

        # Group by meal type
        grouped: dict[str, list] = defaultdict(list)
        for log in logs:
            grouped[log.meal_type].append(DietLogResponse.model_validate(log))

        meal_order = ["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"]
        meals = []
        for meal_type in meal_order:
            if meal_type in grouped:
                meal_logs = grouped[meal_type]
                meals.append(MealGroup(
                    meal_type=meal_type,
                    logs=meal_logs,
                    subtotal_calories=round(sum(l.calories for l in meal_logs), 1),
                    subtotal_protein_g=round(sum(l.protein_g for l in meal_logs), 1),
                    subtotal_carbs_g=round(sum(l.carbs_g for l in meal_logs), 1),
                    subtotal_fat_g=round(sum(l.fat_g for l in meal_logs), 1),
                ))

        total_cal = round(sum(l.calories for l in logs), 1)
        total_prot = round(sum(l.protein_g for l in logs), 1)
        total_carbs = round(sum(l.carbs_g for l in logs), 1)
        total_fat = round(sum(l.fat_g for l in logs), 1)
        total_fiber = round(sum(l.fiber_g for l in logs), 1)

        goal = await self.get_goal(user_id)

        summary = DailyNutritionSummary(
            date=log_date,
            total_calories=total_cal,
            total_protein_g=total_prot,
            total_carbs_g=total_carbs,
            total_fat_g=total_fat,
            total_fiber_g=total_fiber,
            water_ml=water_total,
            goal_calories=goal.daily_calories if goal else None,
            goal_protein_g=goal.protein_g if goal else None,
            goal_carbs_g=goal.carbs_g if goal else None,
            goal_fat_g=goal.fat_g if goal else None,
            goal_water_ml=goal.water_ml if goal else None,
            calorie_remaining=round(goal.daily_calories - total_cal, 1) if goal else None,
            meals=meals,
        )

        await cache_set(cache_key, summary.model_dump(mode="json"), ttl=120)
        return summary

    async def get_week_summary(self, user_id: str, week_start: date) -> NutritionWeekSummary:
        days = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            summary = await self.get_daily_summary(user_id, day)
            days.append(summary)

        logged_days = [d for d in days if d.total_calories > 0]
        n = len(logged_days) or 1

        return NutritionWeekSummary(
            week_start=week_start,
            days=days,
            avg_calories=round(sum(d.total_calories for d in logged_days) / n, 1),
            avg_protein_g=round(sum(d.total_protein_g for d in logged_days) / n, 1),
            avg_carbs_g=round(sum(d.total_carbs_g for d in logged_days) / n, 1),
            avg_fat_g=round(sum(d.total_fat_g for d in logged_days) / n, 1),
        )

    # ── Goals ─────────────────────────────────────────────────────
    async def get_goal(self, user_id: str) -> Optional[NutritionGoal]:
        result = await self.db.execute(
            select(NutritionGoal).where(NutritionGoal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_goal(self, user_id: str, payload: NutritionGoalCreate) -> NutritionGoal:
        goal = await self.get_goal(user_id)
        if goal:
            for field, value in payload.model_dump().items():
                setattr(goal, field, value)
            goal.updated_at = utcnow()
        else:
            goal = NutritionGoal(
                id=str(uuid.uuid4()),
                user_id=user_id,
                **payload.model_dump(),
            )
            self.db.add(goal)
        await self.db.flush()
        return goal

    # ── Water ─────────────────────────────────────────────────────
    async def log_water(self, payload: WaterLogCreate, user_id: str) -> WaterLog:
        log = WaterLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            log_date=payload.log_date,
            amount_ml=payload.amount_ml,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_water_total(self, user_id: str, log_date: date) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(WaterLog.amount_ml), 0))
            .where(WaterLog.user_id == user_id, WaterLog.log_date == log_date)
        )
        return float(result.scalar())
