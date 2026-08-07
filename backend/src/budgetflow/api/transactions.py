"""Transaction routes. DELETE is a soft delete."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas.core import TransactionCreate, TransactionOut, TransactionUpdate
from ..security.deps import get_current_user
from ..services.transaction_service import TransactionError, TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    category_id: int | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TransactionService(db).list(
        user.id, category_id=category_id, limit=limit, offset=offset
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    body: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).create(user.id, **body.model_dump())
    except TransactionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/{tx_id}", response_model=TransactionOut)
async def get_transaction(
    tx_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).get(user.id, tx_id)
    except TransactionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.patch("/{tx_id}", response_model=TransactionOut)
async def update_transaction(
    tx_id: int,
    body: TransactionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).update(user.id, tx_id, **body.model_dump())
    except TransactionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    tx_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await TransactionService(db).soft_delete(user.id, tx_id)
    except TransactionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
