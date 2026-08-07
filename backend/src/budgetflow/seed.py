"""Seed system default categories (user_id NULL, is_system True)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Category

# (name, kind, icon)
SYSTEM_CATEGORIES = [
    ("Salary", "income", "💰"),
    ("Freelance", "income", "🧾"),
    ("Interest", "income", "🏦"),
    ("Food", "expense", "🍽️"),
    ("Groceries", "expense", "🛒"),
    ("Transport", "expense", "🚕"),
    ("Rent", "expense", "🏠"),
    ("Utilities", "expense", "💡"),
    ("Health", "expense", "⚕️"),
    ("Entertainment", "expense", "🎬"),
    ("Shopping", "expense", "🛍️"),
    ("Other", "expense", "📦"),
]


async def seed_system_categories(db: AsyncSession) -> int:
    """Insert any missing system categories. Idempotent. Returns count inserted."""
    existing = await db.execute(select(Category.name).where(Category.is_system.is_(True)))
    have = {row[0] for row in existing.all()}
    inserted = 0
    for name, kind, icon in SYSTEM_CATEGORIES:
        if name in have:
            continue
        db.add(Category(user_id=None, name=name, kind=kind, icon=icon, is_system=True))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted
