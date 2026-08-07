"""Auto-categorization: resolve a free-text hint to one of the user's categories.

Deterministic keyword matching against category names + a small alias map. Keeps
NL-add reliable without an extra LLM round-trip; the AI path can still override.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..services.category_service import CategoryService

# hint keyword -> canonical category name
_ALIASES = {
    "coffee": "Food",
    "restaurant": "Food",
    "lunch": "Food",
    "dinner": "Food",
    "grocery": "Groceries",
    "groceries": "Groceries",
    "uber": "Transport",
    "cab": "Transport",
    "taxi": "Transport",
    "fuel": "Transport",
    "petrol": "Transport",
    "movie": "Entertainment",
    "netflix": "Entertainment",
    "medicine": "Health",
    "doctor": "Health",
    "rent": "Rent",
    "electricity": "Utilities",
    "salary": "Salary",
}


async def categorize(db: AsyncSession, user_id: int, hint: str | None, kind: str) -> int | None:
    """Return a category id matching the hint, or None (falls back to 'Other')."""
    cats = await CategoryService(db).list_for_user(user_id)
    by_name = {c.name.lower(): c for c in cats}

    if hint:
        h = hint.strip().lower()
        if h in by_name and by_name[h].kind == kind:
            return by_name[h].id
        alias = _ALIASES.get(h)
        if alias and alias.lower() in by_name:
            return by_name[alias.lower()].id

    # Default expense bucket if present.
    fallback = "other" if kind == "expense" else None
    if fallback and fallback in by_name:
        return by_name[fallback].id
    return None
