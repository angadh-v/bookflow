from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import BookStatus


class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=255)
    isbn: Optional[str] = Field(default=None, max_length=20)
    publication_year: Optional[int] = Field(default=None, ge=1000, le=2100)
    genre: Optional[str] = Field(default=None, max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=1000)
    summary: Optional[str] = Field(default=None, max_length=5000)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    author: Optional[str] = Field(default=None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(default=None, max_length=20)
    publication_year: Optional[int] = Field(default=None, ge=1000, le=2100)
    genre: Optional[str] = Field(default=None, max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=1000)
    summary: Optional[str] = Field(default=None, max_length=5000)


class BookResponse(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: BookStatus
    borrowed_by: Optional[int] = None
    borrowed_by_auth0_id: Optional[str] = None
    borrowed_by_email: Optional[str] = None
    borrowed_at: Optional[datetime] = None
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    books: Optional[List[BookResponse]] = None
