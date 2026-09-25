from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import settings
from app.core.logging_config import logger

Base = declarative_base()

_engine = None
_async_session_factory = None
active_db_type = "unknown"


async def setup_database_engine():
    global _engine, _async_session_factory, active_db_type

    if _engine is not None:
        return _engine

    primary_url = settings.DATABASE_URL
    try:
        masked_url = primary_url.split('@')[-1] if '@' in primary_url else primary_url
        logger.info(f"Connecting to primary database: {masked_url}")
        test_engine = create_async_engine(primary_url, echo=False, pool_pre_ping=True)
        async with test_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        _engine = test_engine
        active_db_type = "postgresql" if "postgresql" in primary_url else "sqlite"
        logger.info(f"Database connection verified using {active_db_type}")
    except Exception as e:
        if settings.ENABLE_SQLITE_FALLBACK:
            logger.warning(
                f"Primary database connection failed ({e}). "
                f"Falling back to local SQLite engine ({settings.SQLITE_FALLBACK_URL}) for continuous operation."
            )
            _engine = create_async_engine(settings.SQLITE_FALLBACK_URL, echo=False)
            active_db_type = "sqlite"
        else:
            logger.error(f"Failed to connect to database: {e}")
            raise e

    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return _engine


def get_engine():
    global _engine
    return _engine


def get_session_factory():
    global _async_session_factory
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions."""
    global _async_session_factory
    if _async_session_factory is None:
        await setup_database_engine()
    
    async with _async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
