"""Chat routes: assistant turn + session history."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas.chat import ChatRequest, ChatResponse, MessageOut, SessionOut
from ..security.deps import get_current_user
from ..services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ChatService(db).handle(
        user.id, body.message, session_id=body.session_id, provider=body.provider
    )


@router.get("/chat/sessions", response_model=list[SessionOut])
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ChatService(db).list_sessions(user.id)


@router.get("/chat/sessions/{session_id}", response_model=list[MessageOut])
async def session_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ChatService(db).get_messages(user.id, session_id)
