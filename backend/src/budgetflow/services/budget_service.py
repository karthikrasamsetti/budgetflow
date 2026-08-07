"""Budget business logic, including threshold-alert computation."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Budget
from .transaction_service import TransactionService


class BudgetError(Exception):
    pass


class BudgetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tx = TransactionService(db)

    async def create(
        self,
        user_id: int,
        *,
        category_id: int,
        amount: Decimal,
        period: str = "monthly",
        rollover_enabled: bool = False,
        alert_thresholds: list[float] | None = None,
    ) -> Budget:
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            period=period,
            rollover_enabled=rollover_enabled,
            alert_thresholds=alert_thresholds or [0.8, 1.0],
        )
        self.db.add(budget)
        await self.db.commit()
        await self.db.refresh(budget)
        return budget

    async def _get_owned(self, user_id: int, budget_id: int) -> Budget:
        b = await self.db.get(Budget, budget_id)
        if b is None or b.user_id != user_id:
            raise BudgetError("Budget not found")
        return b

    async def list(self, user_id: int) -> list[Budget]:
        result = await self.db.execute(
            select(Budget).where(Budget.user_id == user_id).order_by(Budget.id)
        )
        return list(result.scalars().all())

    async def update(self, user_id: int, budget_id: int, **fields) -> Budget:
        b = await self._get_owned(user_id, budget_id)
        for k, v in fields.items():
            if v is not None:
                setattr(b, k, v)
        await self.db.commit()
        await self.db.refresh(b)
        return b

    async def delete(self, user_id: int, budget_id: int) -> None:
        b = await self._get_owned(user_id, budget_id)
        await self.db.delete(b)
        await self.db.commit()

    async def status(self, user_id: int, budget: Budget, month: str | None = None) -> dict:
        """Spend vs budget for a month, plus which thresholds are crossed."""
        month = month or date.today().strftime("%Y-%m")
        spent = await self.tx.spent_in_month(user_id, budget.category_id, month)
        amount = Decimal(str(budget.amount))
        ratio = float(spent / amount) if amount > 0 else 0.0
        crossed = sorted(t for t in budget.alert_thresholds if ratio >= t)
        return {
            "budget": budget,
            "spent": spent,
            "remaining": amount - spent,
            "ratio": round(ratio, 4),
            "alerts": crossed,
        }
