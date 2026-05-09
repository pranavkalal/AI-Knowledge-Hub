from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./data/llm_dashboard.sqlite3"


class Base(DeclarativeBase):
    # Shared SQLAlchemy base class used by all ORM models.
    pass


# Ensure the local SQLite folder exists before the engine tries to create the
# database file.
Path("data").mkdir(exist_ok=True)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    # Import models so SQLAlchemy registers their table definitions before
    # create_all runs.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        # FastAPI consumes this generator as a request-scoped dependency.
        yield db
    finally:
        db.close()
