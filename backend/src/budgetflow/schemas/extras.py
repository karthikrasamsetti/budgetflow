"""Schemas for Phase 4 extras."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    saved_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    target_date: date | None = None


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    target_date: date | None = None


class GoalContribute(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    saved_amount: Decimal
    target_date: date | None
    model_config = {"from_attributes": True}
