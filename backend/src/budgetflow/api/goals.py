"""Savings goal routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas.extras import GoalContribute, GoalCreate, GoalOut, GoalUpdate
from ..security.deps import get_current_user
from ..services.goal_service import GoalError, GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalOut])
async def list_goals(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await GoalService(db).list(user.id)


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    body: GoalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GoalService(db).create(user.id, **body.model_dump())


@router.post("/{goal_id}/contribute", response_model=GoalOut)
async def contribute(
    goal_id: int,
    body: GoalContribute,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GoalService(db).contribute(user.id, goal_id, body.amount)
    except GoalError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.patch("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: int,
    body: GoalUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GoalService(db).update(user.id, goal_id, **body.model_dump())
    except GoalError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await GoalService(db).delete(user.id, goal_id)
    except GoalError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
