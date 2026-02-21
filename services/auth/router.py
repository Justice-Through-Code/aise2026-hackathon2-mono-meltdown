"""
Auth Service - Handles user registration, login, and profile management.

Bug fixes applied:
- MD5 password hashing replaced with bcrypt
- Secret key moved to environment variable (in shared/config.py)
- Token verification extracted to shared middleware (shared/auth.py)
"""

import sqlite3
import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from services.shared.auth import create_token, verify_token
from services.shared.database import get_connection
from services.shared.models import UserLogin, UserRegister

router = APIRouter(tags=["auth"])


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (replaced insecure MD5)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


@router.post("/register")
async def register(user: UserRegister):
    """Register a new user with bcrypt-hashed password."""
    user_id = str(uuid.uuid4())
    password_hash = hash_password(user.password)

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, user.username, user.email, password_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception:
        raise HTTPException(status_code=500, detail="Registration failed")
    finally:
        conn.close()

    token = create_token(user_id, user.username)

    return {
        "message": "User registered successfully",
        "user_id": user_id,
        "username": user.username,
        "token": token,
    }


@router.post("/login")
async def login(user: UserLogin):
    """Login with username and password. Returns a JWT token."""
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, username, role, password_hash FROM users WHERE username = ? AND is_active = 1",
            (user.username,),
        )
        row = c.fetchone()
    finally:
        conn.close()

    if not row or not verify_password(user.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(row["id"], row["username"], row["role"])

    return {
        "message": "Login successful",
        "token": token,
        "user_id": row["id"],
        "username": row["username"],
    }


@router.get("/me")
async def get_profile(user: dict = Depends(verify_token)):
    """Get the current user's profile and chat statistics."""
    user_id = user["user_id"]

    conn = get_connection()
    try:
        c = conn.cursor()

        c.execute(
            "SELECT id, username, email, created_at, role FROM users WHERE id = ?",
            (user_id,),
        )
        row = c.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        c.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,))
        chat_count = c.fetchone()[0]

        c.execute("SELECT SUM(tokens_used) FROM chat_history WHERE user_id = ?", (user_id,))
        total_tokens = c.fetchone()[0] or 0
    finally:
        conn.close()

    return {
        "user_id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "created_at": row["created_at"],
        "role": row["role"],
        "stats": {
            "total_chats": chat_count,
            "total_tokens_used": total_tokens,
        },
    }
