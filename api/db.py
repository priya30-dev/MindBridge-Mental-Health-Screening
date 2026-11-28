"""Database setup. SQLite by default; set DATABASE_URL for PostgreSQL, e.g.
postgresql+psycopg2://user:pass@host:5432/mindbridge"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

def normalize_db_url(url: str) -> str:
    """Neon/Supabase give "postgresql://..." (or "postgres://..."). SQLAlchemy 2.1 maps that to
    the psycopg v3 driver; we ship psycopg2, so name the driver explicitly."""
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./data/mindbridge.db"))

if DATABASE_URL.startswith("sqlite:///"):
    _db_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", "", 1))
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from api import models_db  # noqa: F401  (registers tables)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
