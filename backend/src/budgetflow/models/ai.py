"""AI / observability models: chat_sessions, messages, ai_logs."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .mixins import SoftDeleteMixin, TimestampMixin


class ChatSession(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", order_by="Message.created_at"
    )


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(12), nullable=False)  # user|assistant|tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class AILog(Base, TimestampMixin):
    """One row per provider call. Powers the AI-usage view."""

    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    intent: Mapped[str] = mapped_column(String(20), nullable=False)  # nl_add|qa|insights|chat
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(10), default="ok")  # ok | error
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
