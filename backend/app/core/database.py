"""
NEXVAULT Control Plane Database Connection & Session Factory
Fully async SQLAlchemy supporting both SQLite (local development) and PostgreSQL.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from backend.app.core.config import settings

# Engine configuration
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

# Enable foreign keys and WAL mode for SQLite
if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
