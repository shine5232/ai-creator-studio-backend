"""Synchronous database layer for Celery workers.

Celery tasks run in separate processes and cannot use the async engine.
This module provides a sync engine/session built from the same DATABASE_URL
(by stripping the +aiosqlite driver).
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_sync_url = settings.DATABASE_URL.replace("+aiosqlite", "")

connect_args = {"check_same_thread": False} if "sqlite" in _sync_url else {}
sync_engine = create_engine(_sync_url, echo=False, connect_args=connect_args)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


@contextmanager
def get_sync_session() -> Generator:
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
