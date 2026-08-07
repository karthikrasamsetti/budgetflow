"""Intent routing. Cheap, deterministic keyword classification decides which of the
three assistant jobs handles a message. This is the seam where a graph engine
(e.g. LangGraph) would slot in if multi-step planning is ever needed.
"""

import re

# An amount + action verb => the user is recording a transaction.
_ADD_RE = re.compile(r"\b(spent|paid|bought|earned|received|got paid|add|record)\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"\d")
_QA_RE = re.compile(
    r"\b(how much|how many|what did|what's my|total|spend|spent on|balance|left)\b",
    re.IGNORECASE,
)
_INSIGHTS_RE = re.compile(
    r"\b(summary|summarize|insight|overview|this month|last month|review|report)\b",
    re.IGNORECASE,
)

NL_ADD, QA, INSIGHTS, CHAT = "nl_add", "qa", "insights", "chat"


def route(message: str) -> str:
    """Return one of: nl_add | qa | insights | chat."""
    has_amount = bool(_AMOUNT_RE.search(message))
    if _ADD_RE.search(message) and has_amount:
        return NL_ADD
    if _QA_RE.search(message):
        return QA
    if _INSIGHTS_RE.search(message):
        return INSIGHTS
    return CHAT
