from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from .config import JWT_ALGORITHM, JWT_EXPIRES_MINUTES, JWT_SECRET

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    def __init__(self, detail: str = "Unauthorized", status_code: int = 401):
        super().__init__(status_code=status_code, detail=detail)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: str, email: str, role: str) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET not configured")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET not configured")

    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


async def get_current_user(creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]) -> dict:
    if creds is None or not creds.credentials:
        raise AuthError()

    try:
        payload = decode_token(creds.credentials)
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role"),
        }
    except jwt.ExpiredSignatureError as e:
        raise AuthError("Token expired") from e
    except jwt.PyJWTError as e:
        raise AuthError("Invalid token") from e


def require_role(*allowed_roles: str):
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise AuthError("Forbidden", status_code=403)
        return user

    return _dep
