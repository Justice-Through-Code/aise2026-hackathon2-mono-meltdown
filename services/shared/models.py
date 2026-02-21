"""
Shared Pydantic models for AISE ASK microservices.
Includes proper input validation.
"""

from typing import Optional

from pydantic import BaseModel, field_validator


class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ContentUpload(BaseModel):
    title: str
    body: str
    content_type: Optional[str] = "lesson"
    metadata: Optional[dict] = None


class ContentSearch(BaseModel):
    query: str
    limit: Optional[int] = 5
