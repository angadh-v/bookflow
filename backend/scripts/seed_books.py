from __future__ import annotations

from sqlalchemy import inspect, text

from app.database import Base, SessionLocal, engine
from app.models import Book


BOOKS = [
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "isbn": "9780061120084",
        "publication_year": 1960,
        "genre": "Classic",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780061120084-L.jpg",
        "summary": "A coming-of-age novel about racial injustice, empathy, and moral courage in the American South.",
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "isbn": "9780451524935",
        "publication_year": 1949,
        "genre": "Dystopian",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780451524935-L.jpg",
        "summary": "A totalitarian state uses surveillance, propaganda, and fear to control truth and human thought.",
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "isbn": "9780743273565",
        "publication_year": 1925,
        "genre": "Classic",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780743273565-L.jpg",
        "summary": "A portrait of wealth, longing, and illusion in the Jazz Age through the mysterious Jay Gatsby.",
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "isbn": "9780141439518",
        "publication_year": 1813,
        "genre": "Romance",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780141439518-L.jpg",
        "summary": "Elizabeth Bennet navigates pride, class, and first impressions in a sharp social comedy.",
    },
    {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "isbn": "9780547928227",
        "publication_year": 1937,
        "genre": "Fantasy",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780547928227-L.jpg",
        "summary": "Bilbo Baggins leaves home on an unexpected quest filled with dragons, riddles, and treasure.",
    },
    {
        "title": "Harry Potter and the Sorcerer's Stone",
        "author": "J.K. Rowling",
        "isbn": "9780590353427",
        "publication_year": 1997,
        "genre": "Fantasy",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780590353427-L.jpg",
        "summary": "A young wizard discovers friendship, danger, and destiny at Hogwarts School of Witchcraft and Wizardry.",
    },
    {
        "title": "The Catcher in the Rye",
        "author": "J.D. Salinger",
        "isbn": "9780316769488",
        "publication_year": 1951,
        "genre": "Literary Fiction",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780316769488-L.jpg",
        "summary": "Holden Caulfield narrates a restless journey through adolescence, alienation, and identity.",
    },
    {
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "isbn": "9780061122415",
        "publication_year": 1988,
        "genre": "Adventure",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780061122415-L.jpg",
        "summary": "A shepherd follows recurring dreams in search of treasure and discovers his personal legend.",
    },
    {
        "title": "The Da Vinci Code",
        "author": "Dan Brown",
        "isbn": "9780307474278",
        "publication_year": 2003,
        "genre": "Thriller",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780307474278-L.jpg",
        "summary": "A symbologist unravels religious puzzles and conspiracies hidden in famous works of art.",
    },
    {
        "title": "The Little Prince",
        "author": "Antoine de Saint-Exupery",
        "isbn": "9780156012195",
        "publication_year": 1943,
        "genre": "Fable",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780156012195-L.jpg",
        "summary": "A poetic tale about love, loneliness, and seeing the essential things invisible to the eye.",
    },
    {
        "title": "The Kite Runner",
        "author": "Khaled Hosseini",
        "isbn": "9781594631931",
        "publication_year": 2003,
        "genre": "Literary Fiction",
        "image_url": "https://covers.openlibrary.org/b/isbn/9781594631931-L.jpg",
        "summary": "A story of friendship, betrayal, and redemption set against decades of Afghanistan's history.",
    },
    {
        "title": "The Curious Incident of the Dog in the Night-Time",
        "author": "Mark Haddon",
        "isbn": "9781400032716",
        "publication_year": 2003,
        "genre": "Mystery",
        "image_url": "https://covers.openlibrary.org/b/isbn/9781400032716-L.jpg",
        "summary": "An autistic teenager investigates a neighborhood mystery and uncovers hidden family truths.",
    },
    {
        "title": "The Book Thief",
        "author": "Markus Zusak",
        "isbn": "9780375842207",
        "publication_year": 2005,
        "genre": "Historical Fiction",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780375842207-L.jpg",
        "summary": "A young girl in Nazi Germany finds solace and resistance through stolen books and words.",
    },
    {
        "title": "The Road",
        "author": "Cormac McCarthy",
        "isbn": "9780307387899",
        "publication_year": 2006,
        "genre": "Post-Apocalyptic",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780307387899-L.jpg",
        "summary": "A father and son travel through a devastated world, clinging to hope and humanity.",
    },
    {
        "title": "The Hunger Games",
        "author": "Suzanne Collins",
        "isbn": "9780439023481",
        "publication_year": 2008,
        "genre": "Dystopian",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780439023481-L.jpg",
        "summary": "Katniss volunteers for a televised fight to the death and sparks a rebellion.",
    },
    {
        "title": "The Help",
        "author": "Kathryn Stockett",
        "isbn": "9780399155345",
        "publication_year": 2009,
        "genre": "Historical Fiction",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780399155345-L.jpg",
        "summary": "Three women challenge racial injustice in 1960s Mississippi by sharing forbidden stories.",
    },
    {
        "title": "Sapiens: A Brief History of Humankind",
        "author": "Yuval Noah Harari",
        "isbn": "9780062316097",
        "publication_year": 2011,
        "genre": "Non-Fiction",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780062316097-L.jpg",
        "summary": "A sweeping account of how Homo sapiens shaped societies, economies, and modern civilization.",
    },
    {
        "title": "Gone Girl",
        "author": "Gillian Flynn",
        "isbn": "9780307588371",
        "publication_year": 2012,
        "genre": "Thriller",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780307588371-L.jpg",
        "summary": "A marriage unravels under media scrutiny when a wife vanishes and suspicion falls on her husband.",
    },
    {
        "title": "The Fault in Our Stars",
        "author": "John Green",
        "isbn": "9780525478812",
        "publication_year": 2012,
        "genre": "Young Adult",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780525478812-L.jpg",
        "summary": "Two teens with cancer fall in love and search for meaning, joy, and honesty.",
    },
    {
        "title": "Educated",
        "author": "Tara Westover",
        "isbn": "9780399590504",
        "publication_year": 2018,
        "genre": "Memoir",
        "image_url": "https://covers.openlibrary.org/b/isbn/9780399590504-L.jpg",
        "summary": "A memoir about leaving an isolated survivalist upbringing to pursue education and self-discovery.",
    },
]


def ensure_schema_compatibility() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    if "books" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("books")}

    with engine.begin() as connection:
        if "summary" not in column_names:
            connection.execute(text("ALTER TABLE books ADD COLUMN summary TEXT"))
        if "image_url" not in column_names:
            connection.execute(text("ALTER TABLE books ADD COLUMN image_url VARCHAR(1000)"))


def seed_books() -> tuple[int, int]:
    ensure_schema_compatibility()

    with SessionLocal() as session:
        existing_isbns = {row[0] for row in session.query(Book.isbn).filter(Book.isbn.isnot(None)).all()}
        to_insert = [item for item in BOOKS if item["isbn"] not in existing_isbns]

        for payload in to_insert:
            session.add(Book(**payload))

        session.commit()
        total_books = session.query(Book).count()

    return len(to_insert), total_books


if __name__ == "__main__":
    inserted, total = seed_books()
    print(f"Inserted {inserted} books. Total catalogue size: {total}.")
