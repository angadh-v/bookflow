from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api import books, chat
from app.config import get_settings
from app.database import Base, engine

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    if "books" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("books")}
    with engine.begin() as connection:
        if "summary" not in column_names:
            connection.execute(text("ALTER TABLE books ADD COLUMN summary TEXT"))
        if "image_url" not in column_names:
            connection.execute(text("ALTER TABLE books ADD COLUMN image_url VARCHAR(1000)"))


@app.on_event("startup")
def on_startup() -> None:
    # For assessment/local use. In production, prefer Alembic migrations.
    Base.metadata.create_all(bind=engine)
    _ensure_schema_compatibility()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(books.router, prefix="/api/books", tags=["books"])
app.include_router(chat.router, prefix="/api/chat", tags=["ai"])
