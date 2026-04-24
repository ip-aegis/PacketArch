# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Database connection and session management."""

from collections.abc import AsyncGenerator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync engine for non-async contexts (e.g., FingerprintCache)
# Convert async URL to sync URL (asyncpg -> psycopg2)
_sync_url = settings.async_database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
sync_engine = create_engine(
    _sync_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=2,  # Smaller pool for sync operations
    max_overflow=3,
)

# Create sync session factory
sync_session_maker = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions.

    IMPORTANT: Transaction Management
    ---------------------------------
    This dependency auto-commits on successful completion and rolls back on exception.

    For route handlers:
    - Do NOT call `await db.commit()` explicitly - it will be handled automatically
    - Use `await db.flush()` if you need to get generated IDs before return
    - Use `await db.refresh(obj)` if you need to reload object state

    Example:
        @router.post("/items")
        async def create_item(db: AsyncSession = Depends(get_db)):
            item = Item(name="example")
            db.add(item)
            await db.flush()  # Get ID without committing
            await db.refresh(item)  # Reload with server defaults
            return item  # Commit happens automatically

    For background tasks (outside request context):
    - Use `async_session_maker()` directly
    - You MUST call `await session.commit()` manually
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_sync_session():
    """Context manager for synchronous database sessions.

    Use this for non-async code that needs database access, such as:
    - FingerprintCache index building
    - Background workers
    - CLI scripts

    Example:
        with get_sync_session() as db:
            templates = db.query(DeviceTemplate).all()

    Note: This uses a separate sync engine with psycopg2 driver.
    Prefer async sessions for request handlers.
    """
    session = sync_session_maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
