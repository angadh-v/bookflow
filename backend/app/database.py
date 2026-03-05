from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()


def normalize_database_url(db_url: str) -> str:
    # Render/Aiven URLs are often provided as mysql://...; force PyMySQL driver.
    if db_url.startswith("mysql://"):
        return "mysql+pymysql://" + db_url[len("mysql://") :]
    return db_url


database_url = normalize_database_url(settings.database_url)

engine_kwargs = {
    "pool_pre_ping": True,
}

if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
