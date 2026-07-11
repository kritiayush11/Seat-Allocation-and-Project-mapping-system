"""
Pydantic schemas for User entity.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["admin"])
    email: EmailStr = Field(..., examples=["admin@ethara.ai"])
    password: str = Field(..., min_length=6, max_length=100, examples=["secretpass"])


class UserLogin(BaseModel):
    username_or_email: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["secretpass"])


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_admin: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
