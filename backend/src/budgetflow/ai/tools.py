"""Tool definitions + dispatch for the Q&A path.

Tools call services, never the DB. Same code paths as the API.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ..services.budget_service import BudgetService
from ..services.category_service import CategoryService
from ..services.transaction_service import TransactionService

# OpenAI/Groq-style function schemas exposed to the model.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_spending_by_category",
            "description": "Total expense spending for a category in a given month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category name, e.g. Food"},
                    "month": {"type": "string", "description": "YYYY-MM; omit for current month"},
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_budgets_status",
            "description": "All budgets with spent/remaining for the current or given month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "YYYY-MM; omit for current"},
                },
            },
        },
    },
]


async def _resolve_category(db: AsyncSession, user_id: int, name: str) -> int | None:
    cats = await CategoryService(db).list_for_user(user_id)
    for c in cats:
        if c.name.lower() == name.strip().lower():
            return c.id
    return None


async def dispatch(db: AsyncSession, user_id: int, name: str, args: dict) -> dict:
    """Execute a tool call by name against the service layer."""
    if name == "get_spending_by_category":
        month = args.get("month") or date.today().strftime("%Y-%m")
        cat_id = await _resolve_category(db, user_id, args["category"])
        if cat_id is None:
            return {"error": f"Unknown category: {args['category']}"}
        spent = await TransactionService(db).spent_in_month(user_id, cat_id, month)
        return {"category": args["category"], "month": month, "spent": str(spent)}

    if name == "list_budgets_status":
        month = args.get("month")
        svc = BudgetService(db)
        out = []
        for b in await svc.list(user_id):
            s = await svc.status(user_id, b, month)
            out.append(
                {
                    "category_id": b.category_id,
                    "budget": str(b.amount),
                    "spent": str(s["spent"]),
                    "remaining": str(s["remaining"]),
                    "alerts": s["alerts"],
                }
            )
        return {"budgets": out}

    return {"error": f"Unknown tool: {name}"}
