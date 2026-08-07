"""Recurring-rule routes + on-demand materialization."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas.core import RecurringCreate, RecurringOut, RecurringUpdate
from ..security.deps import get_current_user
from ..services.recurring_service import RecurringError, RecurringService

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("", response_model=list[RecurringOut])
async def list_recurring(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await RecurringService(db).list(user.id)


@router.post("", response_model=RecurringOut, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    body: RecurringCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await RecurringService(db).create(user.id, **body.model_dump())
    except RecurringError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/run")
async def run_recurring(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Materialize all due rules into transactions. Returns count created."""
    created = await RecurringService(db).materialize_due(user.id)
    return {"created": created}


@router.patch("/{rule_id}", response_model=RecurringOut)
async def update_recurring(
    rule_id: int,
    body: RecurringUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await RecurringService(db).update(user.id, rule_id, **body.model_dump())
    except RecurringError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await RecurringService(db).delete(user.id, rule_id)
    except RecurringError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
