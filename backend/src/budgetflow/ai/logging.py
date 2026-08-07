"""Provider-call logging wrapper.

Every provider call flows through logged_call() so token/latency/cost/status
capture lives in exactly one place and writes one ai_logs row per call.
"""

import time
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AILog
from .base import ChatResult, ToolCallResult

R = TypeVar("R", ChatResult, ToolCallResult)

# Rough per-1K-token cost estimates (USD). Free tiers are ~0; kept for realism
# and so the usage view shows a number. Update as pricing changes.
_COST_PER_1K = {
    "groq": Decimal("0.0"),
    "gemini": Decimal("0.0"),
    "hf": Decimal("0.0"),
}


def _estimate_cost(provider: str, total_tokens: int) -> Decimal:
    rate = _COST_PER_1K.get(provider, Decimal("0.0"))
    return (rate * Decimal(total_tokens) / Decimal(1000)).quantize(Decimal("0.000001"))


async def logged_call(
    db: AsyncSession,
    *,
    provider: str,
    model: str,
    intent: str,
    call: Callable[[], Awaitable[R]],
    user_id: int | None = None,
    session_id: int | None = None,
) -> R:
    """Run an async provider call, timing it and persisting one ai_logs row.

    On success, logs usage + latency. On error, logs status='error' and re-raises
    so callers can handle failure (e.g. fall back to regex parsing).
    """
    start = time.perf_counter()
    log = AILog(
        user_id=user_id,
        session_id=session_id,
        provider=provider,
        model=model,
        intent=intent,
    )
    try:
        result = await call()
    except Exception as exc:  # noqa: BLE001 - we log then re-raise
        log.status = "error"
        log.error = str(exc)[:2000]
        log.latency_ms = int((time.perf_counter() - start) * 1000)
        db.add(log)
        await db.commit()
        raise

    usage = result.usage
    log.status = "ok"
    log.latency_ms = int((time.perf_counter() - start) * 1000)
    log.prompt_tokens = usage.prompt_tokens
    log.completion_tokens = usage.completion_tokens
    log.total_tokens = usage.total_tokens
    log.estimated_cost = _estimate_cost(provider, usage.total_tokens)
    db.add(log)
    await db.commit()
    return result
