from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Book, BookStatus, User
from app.schemas import BookCreate, BookUpdate
from app.services.ai_service import AILibrarian

settings = get_settings()


def list_books(db: Session, skip: int, limit: int) -> list[Book]:
    return db.query(Book).order_by(Book.id.desc()).offset(skip).limit(limit).all()


def search_books(
    db: Session,
    q: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    status_filter: Optional[BookStatus] = None,
) -> list[Book]:
    query = db.query(Book)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Book.title.ilike(like))
            | (Book.author.ilike(like))
            | (Book.genre.ilike(like))
            | (Book.summary.ilike(like))
        )
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if genre:
        query = query.filter(Book.genre.ilike(f"%{genre}%"))
    if status_filter:
        query = query.filter(Book.status == status_filter)

    return query.order_by(Book.id.desc()).all()


def get_book_or_404(db: Session, book_id: int) -> Book:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


def create_book(db: Session, payload: BookCreate) -> Book:
    book = Book(**payload.model_dump())
    db.add(book)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book violates uniqueness constraints") from exc
    db.refresh(book)
    return book


def update_book(db: Session, book_id: int, payload: BookUpdate) -> Book:
    book = get_book_or_404(db, book_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(book, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book violates uniqueness constraints") from exc
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book_or_404(db, book_id)
    db.delete(book)
    db.commit()


def enrich_book_metadata(db: Session, book_id: int) -> Book:
    book = get_book_or_404(db, book_id)
    librarian = AILibrarian(db)
    updates = librarian.enrich_book_metadata(book)
    if not updates:
        return book

    for key, value in updates.items():
        setattr(book, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Enrichment update failed") from exc
    db.refresh(book)
    return book


def checkout_book(db: Session, book_id: int, user: User) -> Book:
    book = db.query(Book).filter(Book.id == book_id).with_for_update().first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book.status == BookStatus.BORROWED:
        if book.borrowed_by == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already borrowed this book")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book already borrowed")

    now = datetime.utcnow()
    book.status = BookStatus.BORROWED
    book.borrowed_by = user.id
    book.borrowed_at = now
    book.due_date = (now + timedelta(days=settings.checkout_days)).date()

    db.commit()
    db.refresh(book)
    return book


def checkin_book(db: Session, book_id: int, user: User) -> Book:
    book = db.query(Book).filter(Book.id == book_id).with_for_update().first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book.status == BookStatus.AVAILABLE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book not currently borrowed")
    if book.borrowed_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the user who borrowed this book can return it",
        )

    book.status = BookStatus.AVAILABLE
    book.borrowed_by = None
    book.borrowed_at = None
    book.due_date = None

    db.commit()
    db.refresh(book)
    return book
