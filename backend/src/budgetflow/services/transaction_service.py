"""Transaction business logic. The single path both the API and AI tools use.

Amounts are stored positive; `kind` decides sign in aggregations.
Deletes are soft (is_deleted / deleted_at); all reads filter them out.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Transaction


def month_bounds(month: str) -> tuple[date, date]:
    """'YYYY-MM' -> (first_day, first_day_of_next_month)."""
    year, mon = (int(x) for x in month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end


class TransactionError(Exception):
    pass


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        *,
        amount: Decimal,
        kind: str,
        occurred_on: date,
        category_id: int | None = None,
        note: str | None = None,
        source: str = "manual",
    ) -> Transaction:
        if kind not in ("income", "expense"):
            raise TransactionError("kind must be 'income' or 'expense'")
        tx = Transaction(
            user_id=user_id,
            amount=amount,
            kind=kind,
            occurred_on=occurred_on,
            category_id=category_id,
            note=note,
            source=source,
        )
        self.db.add(tx)
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def _get_active(self, user_id: int, tx_id: int) -> Transaction:
        tx = await self.db.get(Transaction, tx_id)
        if tx is None or tx.is_deleted or tx.user_id != user_id:
            raise TransactionError("Transaction not found")
        return tx

    async def get(self, user_id: int, tx_id: int) -> Transaction:
        return await self._get_active(user_id, tx_id)

    async def list(
        self,
        user_id: int,
        *,
        category_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.is_deleted.is_(False))
            .order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if category_id is not None:
            stmt = stmt.where(Transaction.category_id == category_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, user_id: int, tx_id: int, **fields) -> Transaction:
        tx = await self._get_active(user_id, tx_id)
        for k, v in fields.items():
            if v is not None:
                setattr(tx, k, v)
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def soft_delete(self, user_id: int, tx_id: int) -> None:
        tx = await self._get_active(user_id, tx_id)
        tx.is_deleted = True
        tx.deleted_at = datetime.now(UTC)
        await self.db.commit()

    async def spent_in_month(self, user_id: int, category_id: int, month: str) -> Decimal:
        """Sum of expense transactions for a category within a month."""
        start, end = month_bounds(month)
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.kind == "expense",
            Transaction.is_deleted.is_(False),
            Transaction.occurred_on >= start,
            Transaction.occurred_on < end,
        )
        return Decimal(str((await self.db.execute(stmt)).scalar_one()))
