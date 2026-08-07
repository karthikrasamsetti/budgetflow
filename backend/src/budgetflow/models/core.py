"""Core domain models: users, categories, accounts, transactions, budgets, recurring, goals."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .mixins import SoftDeleteMixin, TimestampMixin

# Money precision used everywhere. Never float.
MONEY = Numeric(12, 2)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    categories: Mapped[list["Category"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # NULL user_id => system default category, shared by all users.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # income | expense
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User | None"] = relationship(back_populates="categories")


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="cash", nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)


class Transaction(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # positive; sign from kind
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # income | expense
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="manual", nullable=False)

    user: Mapped["User"] = relationship(back_populates="transactions")


class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(10), default="monthly", nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    rollover_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # e.g. [0.8, 1.0] => alert at 80% and 100% of budget.
    alert_thresholds: Mapped[list] = mapped_column(JSON, default=lambda: [0.8, 1.0])


class RecurringRule(Base, TimestampMixin):
    __tablename__ = "recurring_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    cadence: Mapped[str] = mapped_column(String(10), nullable=False)  # daily|weekly|monthly
    next_run_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    saved_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class BudgetRollover(Base, TimestampMixin):
    __tablename__ = "budget_rollovers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    carried_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
