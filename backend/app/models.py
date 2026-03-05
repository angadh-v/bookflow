from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class BookStatus(str, Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    auth0_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    borrowed_books: Mapped[list["Book"]] = relationship("Book", back_populates="borrower")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint(
            "publication_year IS NULL OR (publication_year BETWEEN 1000 AND 2100)",
            name="chk_publication_year",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    isbn: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[BookStatus] = mapped_column(
        SAEnum(BookStatus, name="book_status"), nullable=False, default=BookStatus.AVAILABLE, index=True
    )
    borrowed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    borrowed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    borrower: Mapped[Optional[User]] = relationship("User", back_populates="borrowed_books")

    @property
    def borrowed_by_auth0_id(self) -> Optional[str]:
        if not self.borrower:
            return None
        return self.borrower.auth0_id

    @property
    def borrowed_by_email(self) -> Optional[str]:
        if not self.borrower:
            return None
        return self.borrower.email
