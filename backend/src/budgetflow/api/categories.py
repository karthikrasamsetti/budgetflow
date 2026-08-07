"""Category routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas.core import CategoryCreate, CategoryOut, CategoryUpdate
from ..security.deps import get_current_user
from ..services.category_service import CategoryError, CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await CategoryService(db).list_for_user(user.id)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CategoryService(db).create(user.id, body.name, body.kind, body.icon)
    except CategoryError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CategoryService(db).update(user.id, category_id, **body.model_dump())
    except CategoryError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await CategoryService(db).delete(user.id, category_id)
    except CategoryError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
