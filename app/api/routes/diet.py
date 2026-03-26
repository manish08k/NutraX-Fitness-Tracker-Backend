from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.diet import (
    FoodItemCreate, FoodItemResponse,
    DietLogCreate, DietLogResponse,
    DailyNutritionSummary, NutritionWeekSummary,
    NutritionGoalCreate, NutritionGoalResponse,
    WaterLogCreate, WaterLogResponse,
)
from app.services.diet_service import DietService

router = APIRouter()


# ── Food Database ─────────────────────────────────────────────────
@router.get("/foods", response_model=List[FoodItemResponse])
async def search_foods(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.search_foods(q, limit)


@router.get("/foods/barcode/{barcode}", response_model=FoodItemResponse)
async def get_food_by_barcode(barcode: str, db: AsyncSession = Depends(get_db)):
    service = DietService(db)
    food = await service.get_by_barcode(barcode)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found in database")
    return food


@router.post("/foods", response_model=FoodItemResponse, status_code=201)
async def create_custom_food(
    payload: FoodItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.create_food(payload, current_user.id)


# ── Meal Logs ─────────────────────────────────────────────────────
@router.post("/logs", response_model=DietLogResponse, status_code=201)
async def log_meal(
    payload: DietLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.log_meal(payload, current_user.id)


@router.get("/logs/{log_date}", response_model=DailyNutritionSummary)
async def get_daily_summary(
    log_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.get_daily_summary(current_user.id, log_date)


@router.get("/logs/week/{week_start}", response_model=NutritionWeekSummary)
async def get_week_summary(
    week_start: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.get_week_summary(current_user.id, week_start)


@router.delete("/logs/{log_id}", status_code=204)
async def delete_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    await service.delete_log(log_id, current_user.id)


# ── Nutrition Goals ───────────────────────────────────────────────
@router.put("/goals", response_model=NutritionGoalResponse)
async def set_goals(
    payload: NutritionGoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.upsert_goal(current_user.id, payload)


@router.get("/goals", response_model=NutritionGoalResponse)
async def get_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    goal = await service.get_goal(current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="No nutrition goals set yet")
    return goal


# ── Water Tracking ────────────────────────────────────────────────
@router.post("/water", response_model=WaterLogResponse, status_code=201)
async def log_water(
    payload: WaterLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.log_water(payload, current_user.id)


@router.get("/water/{log_date}", response_model=dict)
async def get_water_for_day(
    log_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    total = await service.get_water_total(current_user.id, log_date)
    goal = await service.get_goal(current_user.id)
    return {
        "date": log_date,
        "total_ml": total,
        "goal_ml": goal.water_ml if goal else 2500.0,
        "percentage": round((total / (goal.water_ml if goal else 2500.0)) * 100, 1),
    }
