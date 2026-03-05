from __future__ import annotations

from typing import Any

import pytest

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.main import app

OWNER_SUB = "auth0|owner-user"
CLIENT_SUB = "auth0|client-user"
OTHER_CLIENT_SUB = "auth0|other-client-user"


def _set_auth_override(sub: str, email: str) -> None:
    def _override_user() -> dict[str, str]:
        return {
            "sub": sub,
            "email": email,
            "name": email.split("@")[0],
        }

    app.dependency_overrides[get_current_user] = _override_user


@pytest.fixture()
def auth_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("OWNER_AUTH0_SUB", OWNER_SUB)
    get_settings.cache_clear()
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_public_list_books_with_auth_enabled(client, auth_enabled):
    app.dependency_overrides.clear()
    response = client.get("/api/books/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_protected_endpoints_require_auth_without_token(client, auth_enabled):
    app.dependency_overrides.clear()

    create_res = client.post("/api/books/", json={"title": "No Auth", "author": "User"})
    assert create_res.status_code == 401

    checkout_res = client.post("/api/books/1/checkout")
    assert checkout_res.status_code == 401

    chat_res = client.post("/api/chat/", json={"message": "hello"})
    assert chat_res.status_code == 401


def test_owner_can_add_update_enrich_and_remove_book(client, auth_enabled):
    _set_auth_override(OWNER_SUB, "owner@example.com")

    create_res = client.post(
        "/api/books/",
        json={
            "title": "Meditations",
            "author": "Marcus Aurelius",
        },
    )
    assert create_res.status_code == 201
    book_id = create_res.json()["id"]

    update_res = client.put(
        f"/api/books/{book_id}",
        json={"genre": "Philosophy", "summary": "Stoic reflections on virtue and discipline."},
    )
    assert update_res.status_code == 200
    assert update_res.json()["genre"] == "Philosophy"

    enrich_res = client.post(f"/api/books/{book_id}/enrich")
    assert enrich_res.status_code == 200

    delete_res = client.delete(f"/api/books/{book_id}")
    assert delete_res.status_code == 204

    get_res = client.get(f"/api/books/{book_id}")
    assert get_res.status_code == 404


def test_client_cannot_modify_catalogue(client, auth_enabled):
    _set_auth_override(OWNER_SUB, "owner@example.com")
    created = client.post("/api/books/", json={"title": "Owned Book", "author": "Owner Author"}).json()
    book_id = created["id"]

    _set_auth_override(CLIENT_SUB, "client@example.com")
    create_res = client.post("/api/books/", json={"title": "Client Book", "author": "Client Author"})
    assert create_res.status_code == 403

    update_res = client.put(f"/api/books/{book_id}", json={"genre": "Forbidden"})
    assert update_res.status_code == 403

    enrich_res = client.post(f"/api/books/{book_id}/enrich")
    assert enrich_res.status_code == 403

    delete_res = client.delete(f"/api/books/{book_id}")
    assert delete_res.status_code == 403


def test_borrow_return_permissions_between_clients(client, auth_enabled):
    _set_auth_override(OWNER_SUB, "owner@example.com")
    create_res = client.post(
        "/api/books/",
        json={"title": "Borrowable Book", "author": "Flow Test", "genre": "Fiction"},
    )
    assert create_res.status_code == 201
    book_id = create_res.json()["id"]

    _set_auth_override(CLIENT_SUB, "client@example.com")
    checkout_res = client.post(f"/api/books/{book_id}/checkout")
    assert checkout_res.status_code == 200
    assert checkout_res.json()["status"] == "borrowed"
    assert checkout_res.json()["borrowed_by_auth0_id"] == CLIENT_SUB

    _set_auth_override(OTHER_CLIENT_SUB, "other@example.com")
    forbidden_checkin = client.post(f"/api/books/{book_id}/checkin")
    assert forbidden_checkin.status_code == 403

    _set_auth_override(CLIENT_SUB, "client@example.com")
    checkin_res = client.post(f"/api/books/{book_id}/checkin")
    assert checkin_res.status_code == 200
    assert checkin_res.json()["status"] == "available"


def test_chat_works_for_authenticated_client(client, auth_enabled):
    _set_auth_override(OWNER_SUB, "owner@example.com")
    create_res = client.post(
        "/api/books/",
        json={
            "title": "The Fault in Our Stars",
            "author": "John Green",
            "genre": "Young Adult",
            "publication_year": 2012,
        },
    )
    assert create_res.status_code == 201

    _set_auth_override(CLIENT_SUB, "client@example.com")
    chat_res = client.post("/api/chat/", json={"message": "books for young adults"})
    assert chat_res.status_code == 200
    payload: dict[str, Any] = chat_res.json()
    assert isinstance(payload.get("reply"), str)
    assert payload.get("books")


def test_enrich_adds_year_and_cover_from_openlibrary_lookup(client, auth_enabled, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    _set_auth_override(OWNER_SUB, "owner@example.com")
    create_res = client.post(
        "/api/books/",
        json={
            "title": "Thinking, Fast and Slow",
            "author": "Daniel Kahneman",
            "genre": "Non-Fiction",
            "summary": "A foundational book on behavioral economics and cognitive bias.",
        },
    )
    assert create_res.status_code == 201
    book_id = create_res.json()["id"]

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "docs": [
                    {
                        "cover_i": 1234567,
                        "first_publish_year": 2011,
                    }
                ]
            }

    monkeypatch.setattr("app.services.ai_service.requests.get", lambda *args, **kwargs: _FakeResponse())

    enrich_res = client.post(f"/api/books/{book_id}/enrich")
    assert enrich_res.status_code == 200
    enriched = enrich_res.json()
    assert enriched["publication_year"] == 2011
    assert enriched["image_url"] == "https://covers.openlibrary.org/b/id/1234567-L.jpg"
