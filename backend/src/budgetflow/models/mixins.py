"""Reusable column mixins."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """created_at set on insert."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Soft-delete columns. Queries filter is_deleted=False by default."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
