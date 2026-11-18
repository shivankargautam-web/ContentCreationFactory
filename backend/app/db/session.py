from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings


def build_engine(settings: Settings) -> AsyncEngine:
    kwargs: dict = {"echo": settings.db_echo, "pool_pre_ping": True}
    if settings.database_url.startswith("postgresql"):
        kwargs.update(pool_size=settings.db_pool_size, max_overflow=settings.db_max_overflow)
    return create_async_engine(settings.database_url, **kwargs)


class Database:
    """Owns the engine and session factory; one instance per process."""

    def __init__(self, settings: Settings) -> None:
        self.engine = build_engine(settings)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        await self.engine.dispose()


_database: Database | None = None


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database(get_settings())
    return _database


def set_database(database: Database | None) -> None:
    global _database
    _database = database
