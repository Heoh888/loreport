from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from loreport_server.config import get_settings

_engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> async_sessionmaker[AsyncSession]:
    global _engine, SessionLocal
    if SessionLocal is not None:
        return SessionLocal

    settings = get_settings()
    connect_args = {}
    if settings.resolved_database_url().startswith("sqlite"):
        connect_args["check_same_thread"] = False
    _engine = create_async_engine(
        settings.resolved_database_url(),
        echo=False,
        connect_args=connect_args,
    )
    SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
    return SessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = _ensure_engine()
    async with factory() as session:
        yield session


async def init_db() -> None:
    from loreport_server.db.models import Base

    _ensure_engine()
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
