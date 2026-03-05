from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base
from app.models import Book, User


DEFAULT_SOURCE_DB_URL = f"sqlite:///{BACKEND_DIR / 'library.db'}"


def normalize_db_url(db_url: str) -> tuple[str, dict]:
    """Normalize provider URL/query params for SQLAlchemy + PyMySQL."""
    connect_args: dict = {}

    if db_url.startswith("mysql://"):
        db_url = "mysql+pymysql://" + db_url[len("mysql://") :]

    parts = urlsplit(db_url)
    if not parts.scheme.startswith("mysql+pymysql"):
        return db_url, connect_args

    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    normalized_pairs = []
    force_ssl = False

    for raw_key, value in query_pairs:
        key = raw_key.replace("-", "_")
        key_lower = key.lower()
        value_lower = value.lower()

        if key_lower == "ssl_mode":
            if value_lower in {"required", "preferred", "verify_ca", "verify_identity", "true", "1", "yes"}:
                force_ssl = True
            continue

        if key_lower == "ssl":
            if value_lower in {"true", "1", "yes", "required"}:
                force_ssl = True
            continue

        normalized_pairs.append((key, value))

    if force_ssl:
        connect_args["ssl"] = {}

    normalized_query = urlencode(normalized_pairs, doseq=True)
    normalized_url = urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))
    return normalized_url, connect_args


def build_engine(db_url: str):
    db_url, normalized_connect_args = normalize_db_url(db_url)
    engine_kwargs = {"pool_pre_ping": True}
    connect_args = {}
    if normalized_connect_args:
        connect_args.update(normalized_connect_args)
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    if connect_args:
        engine_kwargs["connect_args"] = connect_args
    return create_engine(db_url, **engine_kwargs)


def resolve_target_url(cli_value: str | None) -> str:
    if cli_value:
        return cli_value
    for key in ("TARGET_DATABASE_URL", "AIVEN_DATABASE_URL"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise ValueError(
        "Target DB URL missing. Pass --target-db-url or set TARGET_DATABASE_URL/AIVEN_DATABASE_URL."
    )


def upsert_users(source_session, target_session) -> tuple[dict[int, int], int, int]:
    user_id_map: dict[int, int] = {}
    inserted = 0
    updated = 0

    source_users = source_session.query(User).order_by(User.id.asc()).all()
    for src in source_users:
        target = target_session.query(User).filter(User.auth0_id == src.auth0_id).one_or_none()
        if target is None:
            target = User(
                auth0_id=src.auth0_id,
                email=src.email,
                name=src.name,
                created_at=src.created_at,
            )
            target_session.add(target)
            target_session.flush()
            inserted += 1
        else:
            changed = False
            if target.email != src.email:
                target.email = src.email
                changed = True
            if target.name != src.name:
                target.name = src.name
                changed = True
            if src.created_at and target.created_at != src.created_at:
                target.created_at = src.created_at
                changed = True
            if changed:
                updated += 1
        user_id_map[src.id] = target.id

    return user_id_map, inserted, updated


def find_target_book(target_session, source_book: Book) -> Book | None:
    if source_book.isbn:
        by_isbn = target_session.query(Book).filter(Book.isbn == source_book.isbn).one_or_none()
        if by_isbn is not None:
            return by_isbn
    return (
        target_session.query(Book)
        .filter(Book.title == source_book.title, Book.author == source_book.author)
        .one_or_none()
    )


def upsert_books(source_session, target_session, user_id_map: dict[int, int]) -> tuple[int, int]:
    inserted = 0
    updated = 0

    source_books = source_session.query(Book).order_by(Book.id.asc()).all()
    for src in source_books:
        mapped_borrower = user_id_map.get(src.borrowed_by) if src.borrowed_by is not None else None
        payload = {
            "title": src.title,
            "author": src.author,
            "isbn": src.isbn,
            "publication_year": src.publication_year,
            "genre": src.genre,
            "image_url": src.image_url,
            "summary": src.summary,
            "status": src.status,
            "borrowed_by": mapped_borrower,
            "borrowed_at": src.borrowed_at,
            "due_date": src.due_date,
        }

        target = find_target_book(target_session, src)
        if target is None:
            target = Book(**payload, created_at=src.created_at, updated_at=src.updated_at)
            target_session.add(target)
            inserted += 1
            continue

        changed = False
        for field_name, field_value in payload.items():
            if getattr(target, field_name) != field_value:
                setattr(target, field_name, field_value)
                changed = True
        if src.created_at and target.created_at != src.created_at:
            target.created_at = src.created_at
            changed = True
        if src.updated_at and target.updated_at != src.updated_at:
            target.updated_at = src.updated_at
            changed = True
        if changed:
            updated += 1

    return inserted, updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-time copy of local SQLite library data into Aiven MySQL."
    )
    parser.add_argument(
        "--source-db-url",
        default=os.getenv("SOURCE_DATABASE_URL", DEFAULT_SOURCE_DB_URL),
        help=f"Source DB URL (default: {DEFAULT_SOURCE_DB_URL})",
    )
    parser.add_argument(
        "--target-db-url",
        default=None,
        help="Target DB URL (or set TARGET_DATABASE_URL / AIVEN_DATABASE_URL).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run copy logic and print stats, but roll back target transaction.",
    )
    args = parser.parse_args()

    try:
        target_db_url = resolve_target_url(args.target_db_url)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    source_engine = build_engine(args.source_db_url)
    target_engine = build_engine(target_db_url)
    SourceSession = sessionmaker(autocommit=False, autoflush=False, bind=source_engine)
    TargetSession = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)

    Base.metadata.create_all(bind=target_engine)

    try:
        with SourceSession() as source_session, TargetSession() as target_session:
            starting_user_count = target_session.query(User).count()
            starting_book_count = target_session.query(Book).count()
            user_id_map, users_inserted, users_updated = upsert_users(source_session, target_session)
            books_inserted, books_updated = upsert_books(source_session, target_session, user_id_map)
            target_session.flush()

            post_copy_user_count = target_session.query(User).count()
            post_copy_book_count = target_session.query(Book).count()

            if args.dry_run:
                target_session.rollback()
            else:
                target_session.commit()

            if args.dry_run:
                target_user_count = starting_user_count
                target_book_count = starting_book_count
            else:
                target_user_count = target_session.query(User).count()
                target_book_count = target_session.query(Book).count()

        print("Migration complete.")
        print(f"Users: +{users_inserted} inserted, {users_updated} updated")
        print(f"Books: +{books_inserted} inserted, {books_updated} updated")
        if args.dry_run:
            print(f"Target totals after copy (simulated): {post_copy_user_count} users, {post_copy_book_count} books")
            print(f"Target totals after rollback: {target_user_count} users, {target_book_count} books")
        else:
            print(f"Target totals: {target_user_count} users, {target_book_count} books")
        if args.dry_run:
            print("Dry run mode: target changes were rolled back.")
        return 0
    except Exception as exc:  # pragma: no cover - script error reporting
        print(f"Migration failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
