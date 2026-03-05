from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()


def normalize_database_url(db_url: str) -> tuple[str, dict]:
    """
    Normalize DB URLs and query params for SQLAlchemy + PyMySQL.
    - mysql:// -> mysql+pymysql://
    - ssl-mode/ssl_mode -> connect_args['ssl'] toggle
    - hyphenated query keys -> underscore (e.g. ssl-ca -> ssl_ca)
    """
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
        # Minimal TLS enablement for PyMySQL when URL uses mysql client style ssl-mode.
        connect_args["ssl"] = {}

    normalized_query = urlencode(normalized_pairs, doseq=True)
    normalized_url = urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))
    return normalized_url, connect_args


database_url, normalized_connect_args = normalize_database_url(settings.database_url)

engine_kwargs = {
    "pool_pre_ping": True,
}

connect_args = {}
if normalized_connect_args:
    connect_args.update(normalized_connect_args)

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

if connect_args:
    engine_kwargs["connect_args"] = connect_args

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
