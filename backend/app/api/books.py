from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_or_create_user, require_owner
from app.database import get_db
from app.models import BookStatus
from app.schemas import BookCreate, BookResponse, BookUpdate
from app.services import book_service

router = APIRouter()


@router.get("/", response_model=list[BookResponse])
def list_books(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return book_service.list_books(db, skip=skip, limit=limit)


@router.get("/search", response_model=list[BookResponse])
def search_books(
    q: Optional[str] = Query(default=None),
    author: Optional[str] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    status_filter: Optional[BookStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    return book_service.search_books(db, q=q, author=author, genre=genre, status_filter=status_filter)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return book_service.get_book_or_404(db, book_id)


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(
    payload: BookCreate,
    auth_payload: dict = Depends(require_owner),
    db: Session = Depends(get_db),
):
    # Ensure local user record exists for auditing/foreign key references.
    get_or_create_user(auth_payload, db)
    return book_service.create_book(db, payload)


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    payload: BookUpdate,
    auth_payload: dict = Depends(require_owner),
    db: Session = Depends(get_db),
):
    get_or_create_user(auth_payload, db)
    return book_service.update_book(db, book_id, payload)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    auth_payload: dict = Depends(require_owner),
    db: Session = Depends(get_db),
):
    get_or_create_user(auth_payload, db)
    book_service.delete_book(db, book_id)
    return None


@router.post("/{book_id}/checkout", response_model=BookResponse)
def checkout_book(
    book_id: int,
    auth_payload: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = get_or_create_user(auth_payload, db)
    return book_service.checkout_book(db, book_id, user)


@router.post("/{book_id}/enrich", response_model=BookResponse)
def enrich_book(
    book_id: int,
    auth_payload: dict = Depends(require_owner),
    db: Session = Depends(get_db),
):
    get_or_create_user(auth_payload, db)
    return book_service.enrich_book_metadata(db, book_id)


@router.post("/{book_id}/checkin", response_model=BookResponse)
def checkin_book(
    book_id: int,
    auth_payload: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = get_or_create_user(auth_payload, db)
    return book_service.checkin_book(db, book_id, user)
