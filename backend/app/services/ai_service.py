from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
import requests
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Book, BookStatus


@dataclass
class AIResult:
    reply: str
    books: list[Book]


class AISearchIntent(BaseModel):
    query: Optional[str] = Field(
        default=None,
        description="General keyword query when title/author/genre are not explicitly separated.",
        max_length=300,
    )
    author: Optional[str] = Field(default=None, max_length=120)
    genre: Optional[str] = Field(default=None, max_length=60)
    status: Optional[Literal["available", "borrowed"]] = None
    publication_year_from: Optional[int] = Field(default=None, ge=1000, le=2100)
    publication_year_to: Optional[int] = Field(default=None, ge=1000, le=2100)
    limit: int = Field(default=10, ge=1, le=20)


class AIBookMetadata(BaseModel):
    genre: Optional[str] = Field(default=None, max_length=100)
    summary: Optional[str] = Field(default=None, max_length=5000)
    publication_year: Optional[int] = Field(default=None, ge=1000, le=2100)


class AILibrarian:
    """AI-assisted search with safe fallback.

    The implementation intentionally keeps a deterministic fallback path so the
    endpoint remains functional when AI providers are unavailable.
    """

    GENRE_ALIASES = {
        "young adults": "young adult",
        "ya": "young adult",
        "philosophical": "philosophy",
        "sci-fi": "science fiction",
        "scifi": "science fiction",
        "nonfiction": "non-fiction",
    }

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self._llm = None

        if self.settings.ai_enabled and self.settings.openai_api_key:
            try:
                from langchain_openai import ChatOpenAI
            except Exception:
                self._llm = None
            else:
                llm_kwargs: dict[str, Any] = {
                    "openai_api_key": self.settings.openai_api_key,
                    "model_name": self.settings.openai_model,
                    "temperature": 0,
                    "request_timeout": 8,
                    "max_retries": 1,
                }
                if self.settings.openai_base_url:
                    llm_kwargs["openai_api_base"] = self.settings.openai_base_url

                if "openrouter.ai" in self.settings.openai_base_url:
                    headers: dict[str, str] = {}
                    if self.settings.openrouter_site_url:
                        headers["HTTP-Referer"] = self.settings.openrouter_site_url
                    if self.settings.openrouter_app_name:
                        headers["X-Title"] = self.settings.openrouter_app_name
                    if headers:
                        llm_kwargs["default_headers"] = headers

                self._llm = ChatOpenAI(**llm_kwargs)

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
                else:
                    chunks.append(str(item))
            return "\n".join(chunks).strip()
        return str(content).strip()

    @staticmethod
    def _extract_json_object(text: str) -> Optional[dict[str, Any]]:
        if not text:
            return None

        candidates: list[str] = [text.strip()]

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1).strip())

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidates.append(text[start : end + 1].strip())

        for candidate in candidates:
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except (TypeError, ValueError):
                continue
            if isinstance(payload, dict):
                return payload
        return None

    def _lookup_openlibrary_metadata(self, book: Book) -> dict[str, Any]:
        updates: dict[str, Any] = {}

        # Deterministic local fallback: if ISBN exists, we can always provide
        # an OpenLibrary cover URL without any external lookup call.
        if not book.image_url and book.isbn:
            updates["image_url"] = f"https://covers.openlibrary.org/b/isbn/{book.isbn}-L.jpg"

        # External lookup is optional and should never block core behavior.
        # Keep tests deterministic and fast when AI is disabled.
        if not self.settings.ai_enabled:
            return updates

        needs_lookup = (not book.image_url and "image_url" not in updates) or (not book.publication_year)
        if not needs_lookup:
            return updates

        try:
            response = requests.get(
                "https://openlibrary.org/search.json",
                params={
                    "title": book.title,
                    "author": book.author,
                    "limit": 1,
                },
                timeout=3,
            )
            response.raise_for_status()
            payload = response.json()
            docs = payload.get("docs") or []
            if not docs:
                return updates

            top = docs[0]
            if not book.image_url and "image_url" not in updates:
                cover_id = top.get("cover_i")
                if isinstance(cover_id, int):
                    updates["image_url"] = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

            if not book.publication_year:
                first_publish_year = top.get("first_publish_year")
                if isinstance(first_publish_year, int) and 1000 <= first_publish_year <= 2100:
                    updates["publication_year"] = first_publish_year
        except (requests.RequestException, ValueError):
            return updates

        return updates

    def enrich_book_metadata(self, book: Book) -> dict[str, Any]:
        """Return only fields that should be updated for metadata enrichment.

        This method is intentionally best-effort. It should never raise for
        model/network issues and should avoid overwriting existing metadata.
        """
        updates = self._lookup_openlibrary_metadata(book)

        needs_ai = not book.genre or not book.summary or (not book.publication_year and "publication_year" not in updates)
        if not needs_ai or not self.settings.ai_enabled or not self._llm:
            return updates

        from langchain_core.messages import HumanMessage, SystemMessage

        try:
            response = self._llm.invoke(
                [
                    SystemMessage(
                        content=(
                            "You generate concise library metadata for books. "
                            "Infer plausible values and respond ONLY as JSON with keys: "
                            "genre, summary, publication_year. "
                            "Do not invent highly specific factual claims if uncertain."
                        )
                    ),
                    HumanMessage(
                        content=(
                            f"Title: {book.title}\n"
                            f"Author: {book.author}\n"
                            f"Publication year: {book.publication_year or 'Unknown'}\n"
                            f"Existing genre: {book.genre or 'Missing'}\n"
                            f"Existing summary: {book.summary or 'Missing'}\n\n"
                            "Fill missing fields only and return JSON."
                        )
                    ),
                ]
            )
            data = self._extract_json_object(self._content_to_text(response.content))
            if not data:
                return updates
            enrichment = AIBookMetadata.model_validate(data)
        except Exception:
            return updates

        if not book.genre and enrichment.genre:
            genre = enrichment.genre.strip()
            if genre:
                updates["genre"] = genre[:100]

        if not book.summary and enrichment.summary:
            summary = enrichment.summary.strip()
            if summary:
                updates["summary"] = summary[:5000]

        if not book.publication_year and "publication_year" not in updates and enrichment.publication_year:
            year = int(enrichment.publication_year)
            if 1000 <= year <= 2100:
                updates["publication_year"] = year

        return updates

    def _heuristic_filters(self, message: str) -> dict[str, Any]:
        lowered = message.lower()
        filters: dict[str, Any] = {}

        if "available" in lowered:
            filters["status"] = BookStatus.AVAILABLE
        elif "borrowed" in lowered or "checked out" in lowered:
            filters["status"] = BookStatus.BORROWED

        for marker in ["author:", "by "]:
            idx = lowered.find(marker)
            if idx >= 0:
                value = message[idx + len(marker) :].strip()
                if value:
                    filters["author"] = value[:100]
                    break

        genre_tokens = [
            "fiction",
            "non-fiction",
            "science",
            "history",
            "fantasy",
            "biography",
            "philosophy",
            "young adult",
            "young adults",
        ]
        for token in genre_tokens:
            if token in lowered:
                filters["genre"] = self._normalize_genre(token)
                break

        if not filters:
            filters["query"] = message.strip()

        return filters

    def _normalize_genre(self, genre: str) -> str:
        value = (genre or "").strip().lower()
        if not value:
            return ""
        value = value.replace("books", "").strip()
        value = self.GENRE_ALIASES.get(value, value)
        return value

    def _ai_filters(self, message: str) -> dict[str, Any]:
        if not self._llm:
            return {}

        from langchain_core.messages import HumanMessage, SystemMessage

        response = self._llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Extract search filters for a library catalogue query. "
                        "Return ONLY a JSON object with keys: query, author, genre, status, "
                        "publication_year_from, publication_year_to, limit. "
                        "Use null for unknown values. status must be 'available' or 'borrowed'."
                    )
                ),
                HumanMessage(content=message),
            ]
        )

        data = self._extract_json_object(self._content_to_text(response.content))
        if not data:
            return {}
        try:
            intent = AISearchIntent.model_validate(data)
        except Exception:
            return {}

        filters: dict[str, Any] = {}
        if intent.query:
            filters["query"] = intent.query.strip()
        if intent.author:
            filters["author"] = intent.author.strip()
        if intent.genre:
            normalized = self._normalize_genre(intent.genre)
            if normalized:
                filters["genre"] = normalized
        if intent.status:
            filters["status"] = BookStatus(intent.status)
        if intent.publication_year_from:
            filters["publication_year_from"] = intent.publication_year_from
        if intent.publication_year_to:
            filters["publication_year_to"] = intent.publication_year_to
        filters["limit"] = intent.limit
        return filters

    def _search(self, filters: dict[str, Any]) -> list[Book]:
        query = self.db.query(Book)

        if filters.get("query"):
            q = f"%{filters['query']}%"
            query = query.filter(
                (Book.title.ilike(q))
                | (Book.author.ilike(q))
                | (Book.genre.ilike(q))
                | (Book.summary.ilike(q))
            )
        if filters.get("author"):
            query = query.filter(Book.author.ilike(f"%{filters['author']}%"))
        if filters.get("genre"):
            genre_like = f"%{filters['genre']}%"
            query = query.filter((Book.genre.ilike(genre_like)) | (Book.summary.ilike(genre_like)))
        if filters.get("status"):
            query = query.filter(Book.status == filters["status"])
        if filters.get("publication_year_from"):
            query = query.filter(Book.publication_year >= filters["publication_year_from"])
        if filters.get("publication_year_to"):
            query = query.filter(Book.publication_year <= filters["publication_year_to"])

        limit = filters.get("limit", 10)
        return query.order_by(Book.id.desc()).limit(limit).all()

    def _relax_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        relaxed = dict(filters)
        merged_tokens: list[str] = []

        if relaxed.get("genre"):
            merged_tokens.append(str(relaxed.pop("genre")))
        if relaxed.get("author"):
            merged_tokens.append(str(relaxed.pop("author")))
        if relaxed.get("status"):
            # If strict status filtered everything out, retry across all statuses.
            relaxed.pop("status")

        if merged_tokens:
            query = (relaxed.get("query") or "").strip()
            merged = " ".join([query, *merged_tokens]).strip()
            if merged:
                relaxed["query"] = merged

        return relaxed

    def _build_fallback_reply(self, books: list[Book], message: str) -> str:
        if not books:
            return (
                "I could not find matching books. Try adding a title keyword, "
                "an author, a genre, or availability like 'available'."
            )

        top = books[:3]
        snippets = [f"{book.title} by {book.author} ({book.status.value})" for book in top]
        lead = "; ".join(snippets)
        return f"I found {len(books)} matching books for '{message}'. Top matches: {lead}."

    def _build_ai_reply(self, books: list[Book], message: str) -> str:
        if not self._llm:
            return self._build_fallback_reply(books, message)

        from langchain_core.messages import HumanMessage, SystemMessage

        if not books:
            return (
                "I could not find matching books right now. Try broader terms, an author name, "
                "or include availability like 'available'."
            )

        context_lines = [
            f"- {book.title} | {book.author} | {book.genre or 'N/A'} | {book.publication_year or 'N/A'} | {book.status.value}"
            for book in books[:10]
        ]
        context = "\n".join(context_lines)

        response = self._llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a concise librarian assistant. Use only the provided book context. "
                        "Recommend relevant matches and mention availability."
                    )
                ),
                HumanMessage(
                    content=(
                        f"User query: {message}\n\n"
                        f"Book context:\n{context}\n\n"
                        "Write a short helpful response."
                    )
                ),
            ]
        )
        return self._content_to_text(response.content)

    def chat(self, message: str) -> AIResult:
        message = message.strip()
        if not message:
            return AIResult(reply="Please provide a search question.", books=[])

        if not self.settings.ai_enabled:
            filters = self._heuristic_filters(message)
            books = self._search(filters)
            return AIResult(reply=self._build_fallback_reply(books, message), books=books)

        filters: dict[str, Any]
        if self._llm:
            try:
                filters = self._ai_filters(message)
            except Exception:
                filters = self._heuristic_filters(message)
        else:
            filters = self._heuristic_filters(message)

        if not filters:
            filters = self._heuristic_filters(message)
        books = self._search(filters)
        if not books:
            relaxed = self._relax_filters(filters)
            if relaxed != filters:
                books = self._search(relaxed)

        try:
            reply = self._build_ai_reply(books, message)
        except Exception:
            reply = self._build_fallback_reply(books, message)
        return AIResult(reply=reply, books=books)
