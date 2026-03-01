from collections.abc import AsyncGenerator
from loguru import logger

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection, 
    AsyncEngine, 
    AsyncSession,
    async_sessionmaker, 
    create_async_engine, 
)

from app.config import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DB_ASYNC_CONNECTION_STR,
        echo=settings.ENV == "development",
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
        autoflush=False,
    )


engine: AsyncEngine = create_engine()
AsyncSessionLocal: async_sessionmaker[AsyncSession] = create_session_factory(engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.exception("Database error — session rolled back: %s", e)
            raise
        except Exception as e:
            await session.rollback()
            logger.exception("Unexpected error — session rolled back: %s", e)
            raise


async def get_conn() -> AsyncGenerator[AsyncConnection, None]:
    try:
        async with engine.begin() as conn:
            yield conn
    except SQLAlchemyError as e:
        logger.exception("Database connection error: %s", e)
        raise


async def dispose_engine() -> None:
    try:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
    except SQLAlchemyError as e:
        logger.exception("Error disposing database engine: %s", e)
        raise