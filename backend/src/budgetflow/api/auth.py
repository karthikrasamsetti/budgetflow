"""Auth routes. Thin — all logic in AuthService."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_db
from ..models import User
from ..schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from ..security.deps import get_current_user
from ..security.jwt import create_access_token, create_refresh_token, decode_token
from ..security.rate_limit import limiter
from ..services.auth_service import AuthError, AuthService

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.auth_rate_limit)
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService(db).register(body.email, body.password, body.currency)
    except AuthError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit(settings.auth_rate_limit)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService(db).authenticate(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    subject = decode_token(body.refresh_token, expected_type="refresh")
    if subject is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = await db.get(User, int(subject))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return _tokens_for(user)


@router.post("/password-reset/request")
@limiter.limit(settings.auth_rate_limit)
async def password_reset_request(
    request: Request, body: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    user = await service.get_by_email(body.email)
    # Always return 200 to avoid leaking which emails are registered.
    if user is None:
        return {"message": "If that email exists, a reset link has been sent."}
    token = service.create_reset_token(user)
    # In production: email this token as a link; never return it in the response.
    payload = {"message": "If that email exists, a reset link has been sent."}
    if settings.environment == "development":
        payload["debug_reset_token"] = token
    return payload


@router.post("/password-reset/confirm")
async def password_reset_confirm(body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    try:
        await AuthService(db).confirm_reset(body.token, body.new_password)
    except AuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"message": "Password updated."}


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    return current
