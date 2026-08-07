"""Recurring rules + the materializer that turns due rules into transactions."""

from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RecurringRule
from .transaction_service import TransactionService


def advance(d: date, cadence: str) -> date:
    if cadence == "daily":
        return d + timedelta(days=1)
    if cadence == "weekly":
        return d + timedelta(weeks=1)
    if cadence == "monthly":
        return d + relativedelta(months=1)
    raise RecurringError(f"Unknown cadence: {cadence}")


class RecurringError(Exception):
    pass


class RecurringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tx = TransactionService(db)

    async def create(
        self,
        user_id: int,
        *,
        amount: Decimal,
        kind: str,
        cadence: str,
        next_run_on: date,
        category_id: int | None = None,
    ) -> RecurringRule:
        if cadence not in ("daily", "weekly", "monthly"):
            raise RecurringError("cadence must be daily, weekly, or monthly")
        rule = RecurringRule(
            user_id=user_id,
            amount=amount,
            kind=kind,
            cadence=cadence,
            next_run_on=next_run_on,
            category_id=category_id,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def _get_owned(self, user_id: int, rule_id: int) -> RecurringRule:
        r = await self.db.get(RecurringRule, rule_id)
        if r is None or r.user_id != user_id:
            raise RecurringError("Recurring rule not found")
        return r

    async def list(self, user_id: int) -> list[RecurringRule]:
        result = await self.db.execute(
            select(RecurringRule)
            .where(RecurringRule.user_id == user_id)
            .order_by(RecurringRule.next_run_on)
        )
        return list(result.scalars().all())

    async def update(self, user_id: int, rule_id: int, **fields) -> RecurringRule:
        r = await self._get_owned(user_id, rule_id)
        for k, v in fields.items():
            if v is not None:
                setattr(r, k, v)
        await self.db.commit()
        await self.db.refresh(r)
        return r

    async def delete(self, user_id: int, rule_id: int) -> None:
        r = await self._get_owned(user_id, rule_id)
        await self.db.delete(r)
        await self.db.commit()

    async def materialize_due(self, user_id: int, as_of: date | None = None) -> int:
        """Create transactions for every active rule whose next_run_on <= as_of.

        Catches up across multiple missed periods. Returns number of tx created.
        """
        as_of = as_of or date.today()
        result = await self.db.execute(
            select(RecurringRule).where(
                RecurringRule.user_id == user_id,
                RecurringRule.active.is_(True),
                RecurringRule.next_run_on <= as_of,
            )
        )
        rules = list(result.scalars().all())
        created = 0
        for rule in rules:
            run_on = rule.next_run_on
            while run_on <= as_of:
                await self.tx.create(
                    user_id,
                    amount=Decimal(str(rule.amount)),
                    kind=rule.kind,
                    occurred_on=run_on,
                    category_id=rule.category_id,
                    source="recurring",
                )
                created += 1
                run_on = advance(run_on, rule.cadence)
            rule.next_run_on = run_on
        await self.db.commit()
        return created
