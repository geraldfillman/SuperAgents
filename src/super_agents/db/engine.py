"""Database engine factory — swap SQLite/PostgreSQL via connection string."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_DEFAULT_URL = "sqlite:///data/super_agents.db"


def get_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine from a connection URL.

    Reads DATABASE_URL from environment if not provided.
    Defaults to local SQLite for development.
    """
    connection_url = url or os.getenv("DATABASE_URL", _DEFAULT_URL)
    return create_engine(connection_url, echo=False)


@contextmanager
def get_session(url: str | None = None) -> Generator[Session, None, None]:
    """Context manager that yields a SQLAlchemy session and auto-commits."""
    engine = get_engine(url)
    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
