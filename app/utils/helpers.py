from app.schemas.user import TDEEResponse

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "extra_active": 1.9,
}

GOAL_ADJUSTMENTS = {
    "weight_loss": -500,
    "muscle_gain": +300,
    "endurance": +100,
    "flexibility": 0,
    "maintenance": 0,
    "athletic_performance": +200,
}


def calculate_bmr(age: int, weight_kg: float, height_cm: float, gender: str) -> float:
    """Mifflin-St Jeor BMR formula."""
    if gender == "female":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5


def calculate_tdee_full(
    age: int,
    weight_kg: float,
    height_cm: float,
    gender: str,
    activity_level: str,
    goal: str,
) -> TDEEResponse:
    bmr = calculate_bmr(age, weight_kg, height_cm, gender)
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    tdee = bmr * multiplier
    adjustment = GOAL_ADJUSTMENTS.get(goal, 0)
    goal_calories = tdee + adjustment

    # Macro splits based on goal
    if goal == "weight_loss":
        protein_ratio, carb_ratio, fat_ratio = 0.35, 0.35, 0.30
        notes = "High protein to preserve muscle while losing fat. Moderate carbs for energy."
    elif goal == "muscle_gain":
        protein_ratio, carb_ratio, fat_ratio = 0.30, 0.45, 0.25
        notes = "Caloric surplus with high carbs to fuel muscle growth and recovery."
    elif goal == "endurance":
        protein_ratio, carb_ratio, fat_ratio = 0.20, 0.55, 0.25
        notes = "High carbs are essential for endurance performance and glycogen stores."
    elif goal == "athletic_performance":
        protein_ratio, carb_ratio, fat_ratio = 0.28, 0.47, 0.25
        notes = "Balanced macros optimised for performance and recovery."
    else:
        protein_ratio, carb_ratio, fat_ratio = 0.25, 0.50, 0.25
        notes = "Balanced macros for overall health and maintenance."

    return TDEEResponse(
        bmr=round(bmr, 1),
        tdee=round(tdee, 1),
        goal_calories=round(goal_calories, 1),
        protein_g=round((goal_calories * protein_ratio) / 4, 1),
        carbs_g=round((goal_calories * carb_ratio) / 4, 1),
        fat_g=round((goal_calories * fat_ratio) / 9, 1),
        water_ml=round(weight_kg * 35, 0),   # 35ml per kg body weight
        notes=notes,
    )


def estimate_calories_burned(duration_minutes: int, weight_kg: float, activity: str = "strength") -> float:
    """Rough MET-based calorie estimate."""
    MET = {
        "strength": 3.5,
        "cardio": 7.0,
        "hiit": 8.0,
        "yoga": 2.5,
        "cycling": 6.0,
        "running": 8.5,
    }
    met = MET.get(activity, 4.0)
    return round(met * weight_kg * (duration_minutes / 60), 1)
