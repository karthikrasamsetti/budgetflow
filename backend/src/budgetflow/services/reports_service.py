"""Analytical + data services: CSV, rollover, anomalies, AI usage."""

import csv
import io
from collections import defaultdict
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AILog, BudgetRollover, Transaction
from .budget_service import BudgetService
from .transaction_service import TransactionService, month_bounds


class CSVService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export(self, user_id: int) -> str:
        txs = await TransactionService(self.db).list(user_id, limit=100000)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["occurred_on", "kind", "amount", "category_id", "note", "source"])
        for t in txs:
            w.writerow(
                [t.occurred_on, t.kind, t.amount, t.category_id or "", t.note or "", t.source]
            )
        return buf.getvalue()

    async def import_(self, user_id: int, content: str) -> int:
        """Import rows: occurred_on,kind,amount[,category_id,note]. Returns count."""
        svc = TransactionService(self.db)
        reader = csv.DictReader(io.StringIO(content))
        count = 0
        for row in reader:
            try:
                await svc.create(
                    user_id,
                    amount=Decimal(str(row["amount"])),
                    kind=row["kind"].strip(),
                    occurred_on=date.fromisoformat(row["occurred_on"].strip()),
                    category_id=int(row["category_id"]) if row.get("category_id") else None,
                    note=(row.get("note") or None),
                    source="csv",
                )
                count += 1
            except (KeyError, ValueError):
                continue  # skip malformed rows
        return count


class RolloverService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, user_id: int, month: str) -> int:
        """For rollover-enabled budgets, carry unspent amount into `month`.

        Carry = prev-month (budget - spent), floored at 0. Idempotent per month.
        """
        bsvc = BudgetService(self.db)
        prev = (date.fromisoformat(f"{month}-01") - relativedelta(months=1)).strftime("%Y-%m")
        made = 0
        for b in await bsvc.list(user_id):
            if not b.rollover_enabled:
                continue
            existing = await self.db.execute(
                select(BudgetRollover).where(
                    BudgetRollover.budget_id == b.id, BudgetRollover.month == month
                )
            )
            if existing.scalar_one_or_none():
                continue
            status = await bsvc.status(user_id, b, prev)
            carry = max(Decimal("0"), Decimal(str(status["remaining"])))
            self.db.add(
                BudgetRollover(user_id=user_id, budget_id=b.id, month=month, carried_amount=carry)
            )
            made += 1
        await self.db.commit()
        return made


class AnomalyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect(self, user_id: int, month: str, factor: float = 2.0) -> list[dict]:
        """Flag categories whose month spend exceeds `factor`× their trailing average.

        Trailing average uses the 3 months before `month`. Needs prior data to fire.
        """
        start, end = month_bounds(month)
        # Current month per-category spend.
        cur = await self._by_category(user_id, start, end)
        # Trailing 3 months.
        base_start = start - relativedelta(months=3)
        base = await self._by_category(user_id, base_start, start, per_month=3)

        out = []
        for cat_id, spent in cur.items():
            avg = base.get(cat_id, Decimal("0"))
            if avg > 0 and Decimal(str(spent)) >= Decimal(str(avg)) * Decimal(str(factor)):
                out.append(
                    {
                        "category_id": cat_id,
                        "spent": str(spent),
                        "average": str(avg.quantize(Decimal("0.01"))),
                        "ratio": round(float(Decimal(str(spent)) / avg), 2),
                    }
                )
        return out

    async def _by_category(
        self, user_id: int, start: date, end: date, per_month: int = 1
    ) -> dict[int, Decimal]:
        stmt = (
            select(Transaction.category_id, func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.kind == "expense",
                Transaction.is_deleted.is_(False),
                Transaction.occurred_on >= start,
                Transaction.occurred_on < end,
                Transaction.category_id.is_not(None),
            )
            .group_by(Transaction.category_id)
        )
        rows = (await self.db.execute(stmt)).all()
        return {cid: (Decimal(str(total)) / per_month) for cid, total in rows}


class AIUsageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def summary(self, user_id: int) -> dict:
        stmt = select(
            func.count(AILog.id),
            func.coalesce(func.sum(AILog.total_tokens), 0),
            func.coalesce(func.sum(AILog.estimated_cost), 0),
            func.coalesce(func.avg(AILog.latency_ms), 0),
        ).where(AILog.user_id == user_id)
        calls, tokens, cost, latency = (await self.db.execute(stmt)).one()

        by_provider = defaultdict(int)
        rows = await self.db.execute(
            select(AILog.provider, func.count(AILog.id))
            .where(AILog.user_id == user_id)
            .group_by(AILog.provider)
        )
        for prov, n in rows.all():
            by_provider[prov] = n

        return {
            "calls": calls,
            "total_tokens": int(tokens),
            "estimated_cost": str(cost),
            "avg_latency_ms": round(float(latency), 1),
            "by_provider": dict(by_provider),
        }
