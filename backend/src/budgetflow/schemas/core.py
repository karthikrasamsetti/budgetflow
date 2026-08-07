"""Request/response schemas for core resources."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

Kind = str  # "income" | "expense"
Cadence = str  # "daily" | "weekly" | "monthly"


# --- Categories ---
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: Kind
    icon: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    icon: str | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    kind: str
    icon: str | None
    is_system: bool
    model_config = {"from_attributes": True}


# --- Transactions ---
class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    kind: Kind
    occurred_on: date
    category_id: int | None = None
    note: str | None = Field(default=None, max_length=500)
    source: str = "manual"


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    kind: Kind | None = None
    occurred_on: date | None = None
    category_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class TransactionOut(BaseModel):
    id: int
    amount: Decimal
    kind: str
    occurred_on: date
    category_id: int | None
    note: str | None
    source: str
    model_config = {"from_attributes": True}


# --- Budgets ---
class BudgetCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    period: str = "monthly"
    rollover_enabled: bool = False
    alert_thresholds: list[float] = Field(default_factory=lambda: [0.8, 1.0])


class BudgetUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    rollover_enabled: bool | None = None
    alert_thresholds: list[float] | None = None


class BudgetOut(BaseModel):
    id: int
    category_id: int
    amount: Decimal
    period: str
    rollover_enabled: bool
    alert_thresholds: list
    model_config = {"from_attributes": True}


class BudgetStatus(BaseModel):
    """Budget plus current-month spend and which thresholds are breached."""

    budget: BudgetOut
    spent: Decimal
    remaining: Decimal
    ratio: float
    alerts: list[float]  # thresholds crossed, e.g. [0.8] or [0.8, 1.0]


# --- Recurring ---
class RecurringCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    kind: Kind
    cadence: Cadence
    next_run_on: date
    category_id: int | None = None


class RecurringUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    cadence: Cadence | None = None
    next_run_on: date | None = None
    active: bool | None = None


class RecurringOut(BaseModel):
    id: int
    amount: Decimal
    kind: str
    cadence: str
    next_run_on: date
    active: bool
    category_id: int | None
    model_config = {"from_attributes": True}
