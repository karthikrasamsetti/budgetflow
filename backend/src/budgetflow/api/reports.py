"""Reports, CSV data, rollover, and AI-usage routes."""

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..security.deps import get_current_user
from ..services.reports_service import (
    AIUsageService,
    AnomalyService,
    CSVService,
    RolloverService,
)
from ..services.transaction_service import month_bounds  # noqa: F401 (kept for parity)

router = APIRouter(tags=["reports"])


@router.get("/export/csv")
async def export_csv(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await CSVService(db).export(user.id)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@router.post("/import/csv")
async def import_csv(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body = (await request.body()).decode("utf-8")
    count = await CSVService(db).import_(user.id, body)
    return {"imported": count}


@router.post("/budgets/rollover")
async def run_rollover(
    month: str = Query(description="YYYY-MM to carry balances into"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    created = await RolloverService(db).run(user.id, month)
    return {"rollovers": created}


@router.get("/reports/anomalies")
async def anomalies(
    month: str = Query(description="YYYY-MM"),
    factor: float = Query(default=2.0, ge=1.0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"anomalies": await AnomalyService(db).detect(user.id, month, factor)}


@router.get("/ai/usage")
async def ai_usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await AIUsageService(db).summary(user.id)
