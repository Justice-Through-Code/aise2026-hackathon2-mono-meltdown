"""
Shared authentication utilities for AISE ASK microservices.
Provides JWT token creation/verification and a FastAPI dependency for auth.
"""

import time

import jwt
from fastapi import Header, HTTPException

from .config import SECRET_KEY, TOKEN_EXPIRY_SECONDS


def create_token(user_id: str, username: str, role: str = "fellow") -> str:
    """Create a JWT token for a user."""
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": now + TOKEN_EXPIRY_SECONDS,
        "iat": now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(authorization: str = Header(None)) -> dict:
    """FastAPI dependency that verifies a JWT token from the Authorization header.

    Usage in route:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(verify_token)):
            user_id = user["user_id"]
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    try:
        token = authorization.removeprefix("Bearer ").strip()
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
