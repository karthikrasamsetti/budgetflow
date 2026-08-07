"""FastAPI security dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from .jwt import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    subject = decode_token(token, expected_type="access")
    if subject is None:
        raise _credentials_exc
    user = await db.get(User, int(subject))
    if user is None:
        raise _credentials_exc
    return user


__all__ = ["get_current_user", "oauth2_scheme", "select"]
