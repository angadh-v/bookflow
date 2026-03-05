def test_create_list_and_get_book(client):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "isbn": "9780201616224",
        "publication_year": 1999,
        "genre": "Software",
        "image_url": "https://example.com/pragmatic.jpg",
        "summary": "Classic engineering practices for pragmatic software development.",
    }

    create_res = client.post("/api/books/", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["title"] == payload["title"]
    assert created["status"] == "available"
    assert created["image_url"] == payload["image_url"]
    assert created["summary"] == payload["summary"]

    list_res = client.get("/api/books/?skip=0&limit=10")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    get_res = client.get(f"/api/books/{created['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["isbn"] == payload["isbn"]


def test_search_route_is_not_shadowed_by_book_id(client):
    client.post(
        "/api/books/",
        json={
            "title": "Domain-Driven Design",
            "author": "Eric Evans",
            "genre": "Architecture",
        },
    )

    search_res = client.get("/api/books/search?q=Domain")
    assert search_res.status_code == 200
    data = search_res.json()
    assert len(data) == 1
    assert data[0]["author"] == "Eric Evans"


def test_checkout_and_checkin(client):
    create_res = client.post(
        "/api/books/",
        json={
            "title": "Refactoring",
            "author": "Martin Fowler",
            "genre": "Software",
        },
    )
    book_id = create_res.json()["id"]

    checkout_res = client.post(f"/api/books/{book_id}/checkout")
    assert checkout_res.status_code == 200
    checked_out = checkout_res.json()
    assert checked_out["status"] == "borrowed"
    assert checked_out["borrowed_by"] is not None

    checkin_res = client.post(f"/api/books/{book_id}/checkin")
    assert checkin_res.status_code == 200
    checked_in = checkin_res.json()
    assert checked_in["status"] == "available"
    assert checked_in["borrowed_by"] is None


def test_owner_can_enrich_book_metadata(client):
    create_res = client.post(
        "/api/books/",
        json={
            "title": "Clean Architecture",
            "author": "Robert C. Martin",
            "isbn": "9780134494166",
        },
    )
    assert create_res.status_code == 201
    book_id = create_res.json()["id"]

    enrich_res = client.post(f"/api/books/{book_id}/enrich")
    assert enrich_res.status_code == 200
    enriched = enrich_res.json()
    assert enriched["id"] == book_id
    assert enriched["image_url"] == "https://covers.openlibrary.org/b/isbn/9780134494166-L.jpg"


def test_chat_handles_young_adult_phrase(client):
    client.post(
        "/api/books/",
        json={
            "title": "The Fault in Our Stars",
            "author": "John Green",
            "genre": "Young Adult",
            "publication_year": 2012,
        },
    )

    chat_res = client.post("/api/chat/", json={"message": "books for young adults"})
    assert chat_res.status_code == 200
    payload = chat_res.json()
    assert payload["books"]
    assert payload["books"][0]["title"] == "The Fault in Our Stars"
