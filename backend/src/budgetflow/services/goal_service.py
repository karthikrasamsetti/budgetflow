"""Savings goal business logic."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Goal


class GoalError(Exception):
    pass


class GoalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, user_id: int) -> list[Goal]:
        r = await self.db.execute(select(Goal).where(Goal.user_id == user_id).order_by(Goal.id))
        return list(r.scalars().all())

    async def create(self, user_id: int, **fields) -> Goal:
        goal = Goal(user_id=user_id, **fields)
        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)
        return goal

    async def _owned(self, user_id: int, goal_id: int) -> Goal:
        g = await self.db.get(Goal, goal_id)
        if g is None or g.user_id != user_id:
            raise GoalError("Goal not found")
        return g

    async def contribute(self, user_id: int, goal_id: int, amount: Decimal) -> Goal:
        g = await self._owned(user_id, goal_id)
        g.saved_amount = Decimal(str(g.saved_amount)) + amount
        await self.db.commit()
        await self.db.refresh(g)
        return g

    async def update(self, user_id: int, goal_id: int, **fields) -> Goal:
        g = await self._owned(user_id, goal_id)
        for k, v in fields.items():
            if v is not None:
                setattr(g, k, v)
        await self.db.commit()
        await self.db.refresh(g)
        return g

    async def delete(self, user_id: int, goal_id: int) -> None:
        g = await self._owned(user_id, goal_id)
        await self.db.delete(g)
        await self.db.commit()
