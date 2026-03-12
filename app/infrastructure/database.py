from collections.abc import AsyncGenerator
from loguru import logger

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.utils.exceptions import DatabaseError


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DB_ASYNC_CONNECTION_STR,
        echo=settings.DB_ECHO,
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
            logger.exception(
                "Database error; session rolled back",
                event="db_session_failed",
                operation="get_db",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DatabaseError("Database session operation failed") from e
        except Exception as e:
            await session.rollback()
            logger.exception(
                "Unexpected database session error; session rolled back",
                event="db_session_unexpected",
                operation="get_db",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DatabaseError("Unexpected error during database session operation") from e


async def get_conn() -> AsyncGenerator[AsyncConnection, None]:
    try:
        async with engine.begin() as conn:
            yield conn
    except SQLAlchemyError as e:
        logger.exception(
            "Database connection error",
            event="db_connection_failed",
            operation="get_conn",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise DatabaseError("Database connection operation failed") from e


async def dispose_engine() -> None:
    try:
        await engine.dispose()
        logger.info(
            "Database engine disposed successfully",
            event="db_engine_disposed",
            operation="dispose_engine",
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database engine disposal failed",
            event="db_engine_dispose_failed",
            operation="dispose_engine",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise DatabaseError("Database engine disposal failed") from e