"""Budget routes, including per-budget status with threshold alerts."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas.core import BudgetCreate, BudgetOut, BudgetStatus, BudgetUpdate
from ..security.deps import get_current_user
from ..services.budget_service import BudgetError, BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
async def list_budgets(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await BudgetService(db).list(user.id)


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
async def create_budget(
    body: BudgetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BudgetService(db).create(user.id, **body.model_dump())


@router.get("/{budget_id}/status", response_model=BudgetStatus)
async def budget_status(
    budget_id: int,
    month: str | None = Query(default=None, description="YYYY-MM; defaults to current"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BudgetService(db)
    try:
        budget = await service._get_owned(user.id, budget_id)
    except BudgetError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return await service.status(user.id, budget, month)


@router.patch("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: int,
    body: BudgetUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await BudgetService(db).update(user.id, budget_id, **body.model_dump())
    except BudgetError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await BudgetService(db).delete(user.id, budget_id)
    except BudgetError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
