import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException
import google.generativeai as genai

from app.core.config import settings
from app.core.logger import logger
from app.db.redis import cache_get, cache_set
from app.models.workout import WorkoutSession, WorkoutSet, Exercise
from app.models.diet import DietLog
from app.models.user import User


def utcnow():
    return datetime.now(timezone.utc)


class AIService:
    def __init__(self, db: Optional[AsyncSession]):
        self.db = db
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=2048,
            ),
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ],
        )

    def _user_profile_context(self, user: User) -> str:
        parts = [f"User: {user.full_name}"]
        if user.age:
            parts.append(f"Age: {user.age}")
        if user.gender:
            parts.append(f"Gender: {user.gender.value}")
        if user.weight_kg:
            parts.append(f"Weight: {user.weight_kg}kg")
        if user.height_cm:
            parts.append(f"Height: {user.height_cm}cm")
        if user.fitness_goal:
            parts.append(f"Goal: {user.fitness_goal.value.replace('_', ' ')}")
        if user.activity_level:
            parts.append(f"Activity: {user.activity_level.value.replace('_', ' ')}")
        if user.experience_level:
            parts.append(f"Experience: {user.experience_level.value}")
        return " | ".join(parts)

    async def _call_gemini(self, system_prompt: str, user_prompt: str, history: list = None) -> str:
        """Call Gemini with retry on rate limit."""
        for attempt in range(3):
            try:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                if history:
                    # Build conversation from history
                    chat = self.model.start_chat(history=[
                        {"role": msg["role"], "parts": [msg["content"]]}
                        for msg in history
                    ])
                    response = await asyncio.to_thread(chat.send_message, user_prompt)
                else:
                    response = await asyncio.to_thread(
                        self.model.generate_content, full_prompt
                    )
                return response.text
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"Gemini error: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="AI service is temporarily unavailable. Please try again.",
                )

    async def _call_gemini_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Call Gemini and expect JSON response."""
        json_model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=0.4,
                response_mime_type="application/json",
                max_output_tokens=4096,
            ),
        )
        try:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = await asyncio.to_thread(json_model.generate_content, full_prompt)
            return json.loads(response.text)
        except json.JSONDecodeError:
            logger.warning("Gemini returned invalid JSON, falling back to text")
            return {"raw": response.text}
        except Exception as e:
            logger.error(f"Gemini JSON error: {e}")
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable.")

    # ── Multi-turn Chat Coach ─────────────────────────────────────
    async def chat(self, user: User, message: str, conversation_id: Optional[str]) -> dict:
        history_key = f"ai:chat:{user.id}:{conversation_id or 'default'}"
        history = (await cache_get(history_key)) or []

        system = f"""You are GymBrain Coach, a world-class personal trainer and nutritionist AI.
You are helping: {self._user_profile_context(user)}.

Your personality:
- Motivating, direct, and evidence-based
- You personalise every response to the user's profile and goals
- You give specific, actionable advice — not generic tips
- Keep responses concise (3-5 sentences max) unless asked for detail
- Use emojis sparingly for energy 💪
- Never recommend anything that could cause injury or harm
- Always encourage consistency over perfection

You have access to the user's profile. Use it to make advice relevant."""

        # Gemini needs alternating user/model roles
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        reply = await self._call_gemini(system, message, gemini_history if gemini_history else None)

        # Update history (keep last 20 messages = 10 turns)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})
        await cache_set(history_key, history[-20:], ttl=7200)  # 2 hour session

        return {
            "reply": reply,
            "conversation_id": conversation_id or "default",
        }

    # ── Workout Plan Generator ────────────────────────────────────
    async def generate_workout_plan(self, user: User, payload) -> dict:
        cache_key = f"ai:wplan:{user.id}:{payload.days_per_week}:{payload.duration_weeks}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        system = """You are an elite personal trainer. Generate a detailed, progressive workout plan.
Return ONLY valid JSON in this exact structure:
{
  "plan_name": "string",
  "overview": "string",
  "duration_weeks": number,
  "days_per_week": number,
  "weeks": [
    {
      "week": number,
      "theme": "string",
      "days": [
        {
          "day": number,
          "name": "string",
          "muscle_groups": ["string"],
          "estimated_duration_minutes": number,
          "exercises": [
            {
              "name": "string",
              "muscle_group": "string",
              "sets": number,
              "reps": "string",
              "rest_seconds": number,
              "tempo": "string",
              "notes": "string",
              "equipment": "string"
            }
          ],
          "warm_up": ["string"],
          "cool_down": ["string"]
        }
      ]
    }
  ],
  "progression_notes": "string",
  "nutrition_tips": ["string"]
}"""

        prompt = f"""Create a {payload.duration_weeks}-week workout plan for:
{self._user_profile_context(user)}
Days per week: {payload.days_per_week}
Equipment available: {', '.join(payload.available_equipment) or 'bodyweight only'}
Focus areas: {', '.join(payload.focus_areas) or 'full body'}
Session duration: {payload.session_duration_minutes} minutes

Make it progressive — each week slightly harder than the last.
Include warm-up and cool-down for each session.
Tailor exercises to their experience level and goal."""

        result = await self._call_gemini_json(system, prompt)
        await cache_set(cache_key, result, ttl=86400)  # Cache 24h
        return result

    # ── Meal Plan Generator ───────────────────────────────────────
    async def generate_meal_plan(self, user: User, payload) -> dict:
        from app.utils.helpers import calculate_tdee_full
        # Calculate TDEE if profile complete
        tdee_info = None
        if all([user.age, user.weight_kg, user.height_cm]):
            tdee_info = calculate_tdee_full(
                age=user.age,
                weight_kg=user.weight_kg,
                height_cm=user.height_cm,
                gender=user.gender.value if user.gender else "male",
                activity_level=user.activity_level.value if user.activity_level else "moderately_active",
                goal=user.fitness_goal.value if user.fitness_goal else "maintenance",
            )

        system = """You are a certified sports nutritionist. Generate a detailed 7-day meal plan.
Return ONLY valid JSON:
{
  "plan_name": "string",
  "daily_calories": number,
  "macro_targets": {"protein_g": number, "carbs_g": number, "fat_g": number},
  "days": [
    {
      "day": number,
      "day_name": "string",
      "meals": {
        "breakfast": {"name": "string", "ingredients": ["string"], "calories": number, "protein_g": number, "carbs_g": number, "fat_g": number, "prep_time_minutes": number, "recipe_steps": ["string"]},
        "lunch": {"name": "string", "ingredients": ["string"], "calories": number, "protein_g": number, "carbs_g": number, "fat_g": number, "prep_time_minutes": number, "recipe_steps": ["string"]},
        "dinner": {"name": "string", "ingredients": ["string"], "calories": number, "protein_g": number, "carbs_g": number, "fat_g": number, "prep_time_minutes": number, "recipe_steps": ["string"]},
        "snacks": [{"name": "string", "calories": number, "protein_g": number}]
      },
      "total_calories": number,
      "hydration_tips": "string"
    }
  ],
  "grocery_list": {"category": ["items"]},
  "meal_prep_tips": ["string"],
  "supplement_suggestions": ["string"]
}"""

        calories_target = tdee_info["goal_calories"] if tdee_info else 2000

        prompt = f"""Create a 7-day meal plan for:
{self._user_profile_context(user)}
Target calories: {calories_target} kcal/day
Meals per day: {payload.meals_per_day}
Dietary restrictions: {', '.join(payload.dietary_restrictions) or 'none'}
Cuisine preferences: {', '.join(payload.cuisine_preferences) or 'any'}
Include snacks: {payload.include_snacks}

Make it practical with easy-to-find Indian ingredients where possible.
Include full recipe steps for each meal.
Vary the meals across days — no repetition."""

        return await self._call_gemini_json(system, prompt)

    # ── Workout Analysis ─────────────────────────────────────────
    async def analyze_recent_workout(self, user: User) -> dict:
        if not self.db:
            raise HTTPException(status_code=500, detail="Database not available")

        # Fetch last workout
        result = await self.db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user.id)
            .order_by(desc(WorkoutSession.started_at))
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if not session:
            return {"message": "No workouts found yet. Log your first workout to get AI analysis!"}

        await self.db.refresh(session, ["sets"])

        # Get exercise names
        exercise_ids = list({s.exercise_id for s in session.sets})
        ex_result = await self.db.execute(
            select(Exercise).where(Exercise.id.in_(exercise_ids))
        )
        exercises = {e.id: e.name for e in ex_result.scalars().all()}

        # Build workout summary
        sets_summary = []
        for s in session.sets:
            ex_name = exercises.get(s.exercise_id, "Unknown")
            if s.weight_kg and s.reps:
                sets_summary.append(f"{ex_name}: {s.set_number}x{s.reps} @ {s.weight_kg}kg (RPE {s.rpe or 'N/A'})")
            elif s.duration_seconds:
                sets_summary.append(f"{ex_name}: {s.duration_seconds}s")

        prompt = f"""Analyse this workout for {self._user_profile_context(user)}:

Workout: {session.name}
Duration: {(session.duration_seconds or 0) // 60} minutes
Total volume: {session.total_volume_kg}kg
Sets:
{chr(10).join(sets_summary)}

Provide:
1. Performance assessment (what went well)
2. Areas for improvement
3. Recovery recommendations
4. What to focus on next session

Be specific and reference actual numbers from the workout."""

        analysis = await self._call_gemini(
            "You are an expert strength coach analysing workout data. Be specific, data-driven and encouraging.",
            prompt,
        )
        return {
            "session_id": session.id,
            "session_name": session.name,
            "analysis": analysis,
            "generated_at": utcnow().isoformat(),
        }

    # ── Form Tips ────────────────────────────────────────────────
    async def get_form_tips(self, exercise_name: str, user_notes: str, user: User) -> dict:
        prompt = f"""Give expert form tips for: {exercise_name}
User level: {user.experience_level.value if user.experience_level else 'beginner'}
User concern: {user_notes or 'general form check'}

Cover:
1. Setup and starting position
2. Movement execution (step by step)
3. Most common mistakes and how to fix them
4. Breathing pattern
5. Safety cues
6. Beginner vs advanced variations"""

        tips = await self._call_gemini(
            "You are a biomechanics expert and certified personal trainer. Give clear, safe, actionable form advice.",
            prompt,
        )
        return {
            "exercise": exercise_name,
            "tips": tips,
            "generated_at": utcnow().isoformat(),
        }

    # ── Nutrition Advice ─────────────────────────────────────────
    async def nutrition_advice(self, user: User) -> dict:
        if not self.db:
            raise HTTPException(status_code=500, detail="Database not available")

        from datetime import date
        today = date.today()
        result = await self.db.execute(
            select(DietLog)
            .where(DietLog.user_id == user.id, DietLog.log_date == today)
        )
        logs = list(result.scalars().all())

        if not logs:
            return {
                "message": "No food logged today yet. Start logging your meals to get personalised nutrition advice!",
                "tip": "Try logging your breakfast first. Even tracking one meal helps build the habit 🥗",
            }

        total_cal = sum(l.calories for l in logs)
        total_prot = sum(l.protein_g for l in logs)
        total_carbs = sum(l.carbs_g for l in logs)
        total_fat = sum(l.fat_g for l in logs)

        prompt = f"""Give nutrition advice for: {self._user_profile_context(user)}

Today's intake so far:
- Calories: {total_cal:.0f} kcal
- Protein: {total_prot:.0f}g
- Carbs: {total_carbs:.0f}g
- Fat: {total_fat:.0f}g

Meals logged: {', '.join(set(l.meal_type for l in logs))}

Provide:
1. How today's intake looks relative to their goal
2. What macro they should focus on for remaining meals
3. Specific food suggestions for the rest of the day
4. One actionable tip

Keep it short — 4-5 sentences max."""

        advice = await self._call_gemini(
            "You are a sports nutritionist. Give practical, personalised nutrition guidance.",
            prompt,
        )
        return {
            "date": today.isoformat(),
            "current_intake": {
                "calories": round(total_cal, 1),
                "protein_g": round(total_prot, 1),
                "carbs_g": round(total_carbs, 1),
                "fat_g": round(total_fat, 1),
            },
            "advice": advice,
        }

    # ── Motivation ───────────────────────────────────────────────
    async def motivate(self, user: User) -> dict:
        streak = user.current_streak or 0
        workouts = user.total_workouts or 0
        goal = user.fitness_goal.value.replace("_", " ") if user.fitness_goal else "fitness"

        prompt = f"""Generate a short, powerful motivational message for {user.full_name}.
Stats: {workouts} total workouts, {streak}-day streak, goal: {goal}.
Make it personal, energetic, and specific to their journey. Max 2 sentences."""

        message = await self._call_gemini(
            "You are a world-class motivational coach. Be genuine and inspiring.",
            prompt,
        )
        return {
            "message": message,
            "streak": streak,
            "total_workouts": workouts,
        }
