"""Auth business logic. Routes stay thin; this is the reusable core."""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import User
from ..security.hashing import hash_password, verify_password

settings = get_settings()


class AuthError(Exception):
    """Raised for auth failures (bad credentials, duplicate email, bad token)."""


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def register(self, email: str, password: str, currency: str = "INR") -> User:
        if await self.get_by_email(email):
            raise AuthError("Email already registered")
        user = User(email=email, password_hash=hash_password(password), currency=currency)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        return user

    def create_reset_token(self, user: User) -> str:
        """Short-lived signed token. In production this is emailed, not returned."""
        now = datetime.now(UTC)
        payload = {
            "sub": str(user.id),
            "type": "reset",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    async def confirm_reset(self, token: str, new_password: str) -> User:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise AuthError("Invalid or expired reset token") from exc
        if payload.get("type") != "reset":
            raise AuthError("Invalid reset token")
        user = await self.db.get(User, int(payload["sub"]))
        if user is None:
            raise AuthError("User not found")
        user.password_hash = hash_password(new_password)
        await self.db.commit()
        await self.db.refresh(user)
        return user
