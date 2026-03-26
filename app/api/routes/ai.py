from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List

from app.api.deps import get_db, get_current_user, get_premium_user
from app.models.user import User
from app.services.ai_service import AIService

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # For multi-turn chat history


class WorkoutPlanRequest(BaseModel):
    days_per_week: int = 4
    duration_weeks: int = 4
    available_equipment: List[str] = []
    focus_areas: List[str] = []           # e.g. ["chest", "legs"]
    session_duration_minutes: int = 60


class MealPlanRequest(BaseModel):
    dietary_restrictions: List[str] = []  # vegetarian, vegan, gluten-free, etc.
    cuisine_preferences: List[str] = []   # indian, mediterranean, etc.
    meals_per_day: int = 3
    include_snacks: bool = True


class FormCheckRequest(BaseModel):
    exercise_name: str
    user_notes: str = ""                  # What the user is struggling with


@router.post("/chat")
async def chat_with_coach(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Gemini-powered AI fitness coach.
    Maintains conversation history in Redis.
    Available to all users (free tier: 20 msgs/day, premium: unlimited).
    """
    service = AIService(db)

    # Free tier: check daily message limit
    if not current_user.is_premium:
        from app.db.redis import rate_limit_check
        key = f"ai_chat:{current_user.id}"
        allowed, remaining = await rate_limit_check(key, limit=20, window_seconds=86400)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Daily AI message limit reached. Upgrade to Premium for unlimited coaching.",
            )

    return await service.chat(current_user, payload.message, payload.conversation_id)


@router.post("/workout-plan")
async def generate_workout_plan(
    payload: WorkoutPlanRequest,
    current_user: User = Depends(get_premium_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a personalised workout plan using Gemini.
    Premium only.
    """
    service = AIService(db)
    return await service.generate_workout_plan(current_user, payload)


@router.post("/meal-plan")
async def generate_meal_plan(
    payload: MealPlanRequest,
    current_user: User = Depends(get_premium_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a personalised meal plan using Gemini. Premium only."""
    service = AIService(db)
    return await service.generate_meal_plan(current_user, payload)


@router.post("/analyze-workout")
async def analyze_last_workout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyse the user's most recent workout and give AI feedback."""
    service = AIService(db)
    return await service.analyze_recent_workout(current_user)


@router.post("/form-tips")
async def get_form_tips(
    payload: FormCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI tips for correct form on any exercise."""
    service = AIService(db)
    return await service.get_form_tips(payload.exercise_name, payload.user_notes, current_user)


@router.get("/nutrition-advice")
async def get_nutrition_advice(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get personalised nutrition advice based on today's diet log."""
    service = AIService(db)
    return await service.nutrition_advice(current_user)


@router.get("/motivate")
async def get_motivation(current_user: User = Depends(get_current_user)):
    """Get a personalised motivational message from your AI coach."""
    from app.services.ai_service import AIService
    service = AIService(None)
    return await service.motivate(current_user)
