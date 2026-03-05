from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_or_create_user
from app.database import get_db
from app.schemas import BookResponse, ChatRequest, ChatResponse
from app.services.ai_service import AILibrarian

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    auth_payload: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_or_create_user(auth_payload, db)
    librarian = AILibrarian(db)
    result = librarian.chat(payload.message)
    books = [BookResponse.model_validate(book) for book in result.books]
    return ChatResponse(reply=result.reply, books=books)
