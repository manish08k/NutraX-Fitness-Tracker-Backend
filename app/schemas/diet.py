from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime


class FoodItemCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    serving_size_g: float = 100.0
    calories_per_100g: float
    protein_per_100g: float = 0.0
    carbs_per_100g: float = 0.0
    fat_per_100g: float = 0.0
    fiber_per_100g: float = 0.0
    sugar_per_100g: float = 0.0
    sodium_mg_per_100g: float = 0.0
    barcode: Optional[str] = None


class FoodItemResponse(FoodItemCreate):
    id: str
    is_verified: bool
    is_custom: bool
    model_config = {"from_attributes": True}


class DietLogCreate(BaseModel):
    log_date: date
    meal_type: str
    food_item_id: str
    quantity_g: float

    @field_validator("meal_type")
    @classmethod
    def valid_meal_type(cls, v):
        valid = {"breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"}
        if v not in valid:
            raise ValueError(f"meal_type must be one of: {', '.join(valid)}")
        return v

    @field_validator("quantity_g")
    @classmethod
    def positive_quantity(cls, v):
        if v <= 0:
            raise ValueError("quantity_g must be positive")
        return v


class DietLogResponse(BaseModel):
    id: str
    user_id: str
    log_date: date
    meal_type: str
    food_item_id: str
    food_name: str
    quantity_g: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    logged_at: datetime
    model_config = {"from_attributes": True}


class MealGroup(BaseModel):
    meal_type: str
    logs: List[DietLogResponse]
    subtotal_calories: float
    subtotal_protein_g: float
    subtotal_carbs_g: float
    subtotal_fat_g: float


class DailyNutritionSummary(BaseModel):
    date: date
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    water_ml: float
    goal_calories: Optional[float]
    goal_protein_g: Optional[float]
    goal_carbs_g: Optional[float]
    goal_fat_g: Optional[float]
    goal_water_ml: Optional[float]
    calorie_remaining: Optional[float]
    meals: List[MealGroup]


class NutritionGoalCreate(BaseModel):
    daily_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 25.0
    water_ml: float = 2500.0


class NutritionGoalResponse(NutritionGoalCreate):
    id: str
    user_id: str
    updated_at: datetime
    model_config = {"from_attributes": True}


class WaterLogCreate(BaseModel):
    log_date: date
    amount_ml: float

    @field_validator("amount_ml")
    @classmethod
    def positive_amount(cls, v):
        if v <= 0:
            raise ValueError("amount_ml must be positive")
        return v


class WaterLogResponse(BaseModel):
    id: str
    amount_ml: float
    logged_at: datetime
    model_config = {"from_attributes": True}


class NutritionWeekSummary(BaseModel):
    week_start: date
    days: List[DailyNutritionSummary]
    avg_calories: float
    avg_protein_g: float
    avg_carbs_g: float
    avg_fat_g: float
