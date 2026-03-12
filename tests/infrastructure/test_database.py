from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.infrastructure.database import (
    create_engine,
    create_session_factory,
    dispose_engine,
    get_conn,
    get_db,
)
from app.utils.exceptions import DatabaseError


class TestCreateEngine:

    def test_returns_async_engine(self):
        with patch("app.infrastructure.database.create_async_engine") as mock:
            mock.return_value = MagicMock(spec=AsyncEngine)
            result = create_engine()
            assert result is mock.return_value

    def test_called_with_correct_args(self):
        with patch("app.infrastructure.database.create_async_engine") as mock:
            mock.return_value = MagicMock(spec=AsyncEngine)
            create_engine()
            mock.assert_called_once_with(
                settings.DB_ASYNC_CONNECTION_STR,
                echo=settings.DB_ECHO,
                future=True,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )


class TestCreateSessionFactory:

    def test_returns_sessionmaker(self):
        mock_engine = MagicMock(spec=AsyncEngine)
        with patch("app.infrastructure.database.async_sessionmaker") as mock:
            mock.return_value = MagicMock()
            result = create_session_factory(mock_engine)
            assert result is mock.return_value

    def test_called_with_correct_args(self):
        mock_engine = MagicMock(spec=AsyncEngine)
        with patch("app.infrastructure.database.async_sessionmaker") as mock:
            mock.return_value = MagicMock()
            create_session_factory(mock_engine)
            mock.assert_called_once_with(
                bind=mock_engine,
                expire_on_commit=False,
                class_=AsyncSession,
                autoflush=False,
            )


class TestGetDb:

    @pytest.fixture
    def mock_factory(self):
        mock_session = AsyncMock(spec=AsyncSession)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        return MagicMock(return_value=mock_cm), mock_session

    async def test_yields_session(self, mock_factory):
        factory, mock_session = mock_factory
        with patch("app.infrastructure.database.AsyncSessionLocal", factory):
            gen = get_db()
            session = await gen.asend(None)
            assert session is mock_session
            await gen.aclose()

    async def test_rolls_back_on_sqlalchemy_error(self, mock_factory):
        factory, mock_session = mock_factory
        with patch("app.infrastructure.database.AsyncSessionLocal", factory):
            gen = get_db()
            await gen.asend(None)
            with pytest.raises(DatabaseError):
                await gen.athrow(SQLAlchemyError("db error"))
        mock_session.rollback.assert_awaited_once()

    async def test_rolls_back_on_generic_exception(self, mock_factory):
        factory, mock_session = mock_factory
        with patch("app.infrastructure.database.AsyncSessionLocal", factory):
            gen = get_db()
            await gen.asend(None)
            with pytest.raises(DatabaseError):
                await gen.athrow(RuntimeError("unexpected"))
        mock_session.rollback.assert_awaited_once()

    async def test_reraises_sqlalchemy_error(self, mock_factory):
        factory, _ = mock_factory
        error = SQLAlchemyError("db error")
        with patch("app.infrastructure.database.AsyncSessionLocal", factory):
            gen = get_db()
            await gen.asend(None)
            with pytest.raises(DatabaseError) as exc_info:
                await gen.athrow(error)
        assert isinstance(exc_info.value.__cause__, SQLAlchemyError)

    async def test_reraises_generic_exception(self, mock_factory):
        factory, _ = mock_factory
        error = RuntimeError("unexpected")
        with patch("app.infrastructure.database.AsyncSessionLocal", factory):
            gen = get_db()
            await gen.asend(None)
            with pytest.raises(DatabaseError) as exc_info:
                await gen.athrow(error)
        assert isinstance(exc_info.value.__cause__, RuntimeError)


class TestGetConn:

    @pytest.fixture
    def mock_engine(self):
        mock_conn = AsyncMock(spec=AsyncConnection)
        mock_begin_cm = AsyncMock()
        mock_begin_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin_cm.__aexit__ = AsyncMock(return_value=False)
        engine = MagicMock(spec=AsyncEngine)
        engine.begin = MagicMock(return_value=mock_begin_cm)
        return engine, mock_conn

    async def test_yields_connection(self, mock_engine):
        engine, mock_conn = mock_engine
        with patch("app.infrastructure.database.engine", engine):
            gen = get_conn()
            conn = await gen.asend(None)
            assert conn is mock_conn
            await gen.aclose()

    async def test_reraises_sqlalchemy_error(self, mock_engine):
        engine, _ = mock_engine
        error = SQLAlchemyError("connection error")
        with patch("app.infrastructure.database.engine", engine):
            gen = get_conn()
            await gen.asend(None)
            with pytest.raises(DatabaseError) as exc_info:
                await gen.athrow(error)
        assert isinstance(exc_info.value.__cause__, SQLAlchemyError)


class TestDisposeEngine:

    async def test_disposes_engine(self):
        mock_engine = AsyncMock(spec=AsyncEngine)
        with patch("app.infrastructure.database.engine", mock_engine):
            await dispose_engine()
        mock_engine.dispose.assert_awaited_once()

    async def test_reraises_sqlalchemy_error(self):
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.dispose.side_effect = SQLAlchemyError("dispose error")
        with patch("app.infrastructure.database.engine", mock_engine):
            with pytest.raises(DatabaseError):
                await dispose_engine()
