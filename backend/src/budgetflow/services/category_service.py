"""Category business logic. System categories (user_id NULL) are read-only to users."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Category


class CategoryError(Exception):
    pass


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: int) -> list[Category]:
        """System defaults + this user's own categories."""
        result = await self.db.execute(
            select(Category)
            .where(or_(Category.user_id == user_id, Category.is_system.is_(True)))
            .order_by(Category.kind, Category.name)
        )
        return list(result.scalars().all())

    async def get_owned(self, user_id: int, category_id: int) -> Category:
        cat = await self.db.get(Category, category_id)
        if cat is None or cat.is_system or cat.user_id != user_id:
            raise CategoryError("Category not found")
        return cat

    async def create(self, user_id: int, name: str, kind: str, icon: str | None) -> Category:
        if kind not in ("income", "expense"):
            raise CategoryError("kind must be 'income' or 'expense'")
        cat = Category(user_id=user_id, name=name, kind=kind, icon=icon, is_system=False)
        self.db.add(cat)
        await self.db.commit()
        await self.db.refresh(cat)
        return cat

    async def update(self, user_id: int, category_id: int, **fields) -> Category:
        cat = await self.get_owned(user_id, category_id)
        for k, v in fields.items():
            if v is not None:
                setattr(cat, k, v)
        await self.db.commit()
        await self.db.refresh(cat)
        return cat

    async def delete(self, user_id: int, category_id: int) -> None:
        cat = await self.get_owned(user_id, category_id)
        await self.db.delete(cat)
        await self.db.commit()
