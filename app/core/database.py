from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def build_engine_and_session(db_url: str | None = None) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    url = db_url or settings.DATABASE_URL
    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False

    eng = create_async_engine(
        url,
        echo=settings.DB_ECHO,
        connect_args=connect_args,
        future=True,
    )

    session_maker = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return eng, session_maker


engine, AsyncSessionLocal = build_engine_and_session()


def set_database_url(new_url: str) -> None:
    """Updates global engine and sessionmaker to point to new database URL."""
    global engine, AsyncSessionLocal
    engine, AsyncSessionLocal = build_engine_and_session(new_url)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    # Ensure models are imported so Base.metadata knows about them
    import app.models.job
    import app.models.certificate
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
