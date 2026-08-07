"""NL-add parsing. Primary path is provider structured output (in the service);
this module is the deterministic regex fallback used when a provider call fails
or returns nothing usable.
"""

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

_AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:[.,]\d{1,2})?)", re.IGNORECASE)
_INCOME_HINTS = ("earned", "received", "got paid", "salary", "income", "credited")
# "on food", "for groceries", "at starbucks" -> category-ish token
_CATEGORY_RE = re.compile(r"\b(?:on|for|at)\s+([a-zA-Z][a-zA-Z &]+)", re.IGNORECASE)


def _relative_date(text: str, today: date) -> date:
    t = text.lower()
    if "yesterday" in t:
        return today - timedelta(days=1)
    if "today" in t:
        return today
    return today


def has_relative_date(text: str) -> bool:
    """True if the message explicitly anchors a date we should compute ourselves."""
    t = text.lower()
    return "today" in t or "yesterday" in t


def resolve_relative_date(text: str, today: date | None = None) -> date:
    """Public resolver for 'today'/'yesterday'; defaults to today."""
    return _relative_date(text, today or date.today())


def parse_nl_add(text: str, *, today: date | None = None) -> dict | None:
    """Best-effort extraction. Returns {amount, kind, occurred_on, category_hint, note}
    or None if no amount is found (nothing to record)."""
    today = today or date.today()
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(",", ".")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        return None
    if amount <= 0:
        return None

    kind = "income" if any(h in text.lower() for h in _INCOME_HINTS) else "expense"

    category_hint = None
    cm = _CATEGORY_RE.search(text)
    if cm:
        category_hint = cm.group(1).strip().split(" ")[0].capitalize()

    return {
        "amount": amount,
        "kind": kind,
        "occurred_on": _relative_date(text, today),
        "category_hint": category_hint,
        "note": text.strip()[:500],
    }