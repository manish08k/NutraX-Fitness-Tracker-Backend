import uuid
from datetime import datetime, date, timezone
from sqlalchemy import (
    String, Float, Integer, Date, DateTime,
    ForeignKey, Boolean, Text, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.postgres import Base


def utcnow():
    return datetime.now(timezone.utc)


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serving_size_g: Mapped[float] = mapped_column(Float, default=100.0)       # Reference serving

    # Macros per 100g
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, default=0.0)
    carbs_per_100g: Mapped[float] = mapped_column(Float, default=0.0)
    fat_per_100g: Mapped[float] = mapped_column(Float, default=0.0)
    fiber_per_100g: Mapped[float] = mapped_column(Float, default=0.0)
    sugar_per_100g: Mapped[float] = mapped_column(Float, default=0.0)
    sodium_mg_per_100g: Mapped[float] = mapped_column(Float, default=0.0)

    barcode: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)         # Verified by admin
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DietLog(Base):
    __tablename__ = "diet_logs"
    __table_args__ = (
        Index("ix_diet_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)        # breakfast/lunch/dinner/snack
    food_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("food_items.id", ondelete="RESTRICT"), nullable=False)
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)       # Snapshot — in case food is deleted
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False)

    # Calculated at log time — avoid re-computing
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, default=0.0)
    fiber_g: Mapped[float] = mapped_column(Float, default=0.0)

    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NutritionGoal(Base):
    __tablename__ = "nutrition_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    daily_calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_g: Mapped[float] = mapped_column(Float, default=25.0)
    water_ml: Mapped[float] = mapped_column(Float, default=2500.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WaterLog(Base):
    __tablename__ = "water_logs"
    __table_args__ = (
        Index("ix_water_user_date", "user_id", "log_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_ml: Mapped[float] = mapped_column(Float, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
