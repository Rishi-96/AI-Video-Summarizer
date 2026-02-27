import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8")[:72],
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8")[:72],
        bcrypt.gensalt(),
    ).decode("utf-8")


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Token verification helpers
# ---------------------------------------------------------------------------

def _decode_token(token: str, expected_type: str) -> Optional[str]:
    """Return the 'sub' claim or None on any error."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency: extract and validate current user from Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = _decode_token(token, "access")
    if user_id is None:
        raise credentials_exception

    from ..api.auth import get_user_by_id
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_from_token(token: str) -> Optional[dict]:
    """
    Non-raising variant for WebSocket auth.
    Returns the user dict or None if token is invalid / user not found.
    """
    if not token:
        return None

    user_id = _decode_token(token, "access")
    if user_id is None:
        return None

    from ..api.auth import get_user_by_id
    return await get_user_by_id(user_id)


async def get_current_user_from_refresh(token: str) -> Optional[dict]:
    """Validate a refresh token and return the user."""
    user_id = _decode_token(token, "refresh")
    if user_id is None:
        return None

    from ..api.auth import get_user_by_id
    return await get_user_by_id(user_id)