"""Chat request/response schemas."""

from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    provider: str | None = None


class ChatResponse(BaseModel):
    session_id: int
    intent: str
    reply: str
    action: dict | None = None


class SessionOut(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}
