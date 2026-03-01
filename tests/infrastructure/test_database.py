import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker

from app.infrastructure.database import (
    AsyncSessionLocal,
    create_engine,
    create_session_factory,
    dispose_engine,
    engine,
    get_conn,
    get_db,
)


# ===========================================================================
# Helpers
# ===========================================================================

def make_mock_session() -> tuple[AsyncMock, MagicMock]:
    """Returns (mock_session, mock_context_manager) for patching AsyncSessionLocal."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_session, mock_cm


def make_mock_conn() -> tuple[AsyncMock, MagicMock]:
    """Returns (mock_connection, mock_context_manager) for patching engine.begin()."""
    mock_conn = AsyncMock(spec=AsyncConnection)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_conn, mock_cm


MODULE = "app.infrastructure.database"

class TestCreateEngine:

    # ------------------------------------------------------------------
    # Test 1 – Returns an AsyncEngine
    # Name: create_engine returns AsyncEngine
    # Description: create_engine() should return an AsyncEngine instance.
    # Steps: Call create_engine(); check the return type.
    # Expected: isinstance(result, AsyncEngine) is True
    # ------------------------------------------------------------------
    def test_returns_async_engine(self):
        result = create_engine()
        assert isinstance(result, AsyncEngine)

    # ------------------------------------------------------------------
    # Test 3 – echo=True in development
    # Name: Echo enabled in development
    # Description: echo should be True when DEBUG == True.
    # Steps: Patch settings.DEBUG to True; call create_engine().
    # Expected: result.echo is True
    # ------------------------------------------------------------------
    def test_echo_true_in_development(self):
        from app.config import settings
        with patch.object(settings, "DEBUG", True):
            result = create_engine()
            assert result.echo is True

    # ------------------------------------------------------------------
    # Test 4 – echo=False outside development
    # Name: Echo disabled outside development
    # Description: echo should be False when DEBUG != True.
    # Steps: Patch settings.DEBUG to False; call create_engine().
    # Expected: result.echo is False
    # ------------------------------------------------------------------
    def test_echo_false_in_production(self):
        from app.config import settings
        with patch.object(settings, "DEBUG", False):
            result = create_engine()
            assert result.echo is False

    # ------------------------------------------------------------------
    # Test 5 – pool_pre_ping is enabled
    # Name: pool_pre_ping enabled
    # Description: pool_pre_ping=True prevents stale connections being used.
    # Steps: Call create_engine(); check pool._pre_ping.
    # Expected: engine.pool._pre_ping is True
    # ------------------------------------------------------------------
    def test_pool_pre_ping_enabled(self):
        result = create_engine()
        assert result.pool._pre_ping is True

    # ------------------------------------------------------------------
    # Test 6 – dialect is set
    # Name: Engine has a dialect
    # Description: A valid engine should always have a dialect configured.
    # Steps: Call create_engine(); check engine.dialect.
    # Expected: result.dialect is not None
    # ------------------------------------------------------------------
    def test_has_dialect(self):
        result = create_engine()
        assert result.dialect is not None


# ===========================================================================
# create_engine()
# ===========================================================================

class TestCreateEngine:

    # ------------------------------------------------------------------
    # Test 1 – Returns an AsyncEngine
    # Name: create_engine returns AsyncEngine
    # Description: create_engine() should return an AsyncEngine instance.
    # Steps: Call create_engine(); check the return type.
    # Expected: isinstance(result, AsyncEngine) is True
    # ------------------------------------------------------------------
    def test_returns_async_engine(self):
        result = create_engine()
        assert isinstance(result, AsyncEngine)

    # ------------------------------------------------------------------
    # Test 2 – URL matches settings
    # Name: Engine URL matches settings
    # Description: The engine URL should match DB_ASYNC_CONNECTION_STR.
    # Steps: Call create_engine(); compare URL to settings.
    # Expected: str(result.url) == settings.DB_ASYNC_CONNECTION_STR
    # ------------------------------------------------------------------
    def test_url_matches_settings(self):
        from app.config import settings
        result = create_engine()
        assert result.url.render_as_string(hide_password=False) == settings.DB_ASYNC_CONNECTION_STR

    # ------------------------------------------------------------------
    # Test 3 – echo=True in development
    # Name: Echo enabled in development
    # Description: echo should be True when ENV == "development".
    # Steps: Patch settings.ENV to "development"; call create_engine().
    # Expected: result.echo is True
    # ------------------------------------------------------------------
    def test_echo_true_in_development(self):
        from app.config import settings
        with patch.object(settings, "ENV", "development"):
            result = create_engine()
            assert result.echo is True

    # ------------------------------------------------------------------
    # Test 4 – echo=False outside development
    # Name: Echo disabled outside development
    # Description: echo should be False when ENV != "development".
    # Steps: Patch settings.ENV to "production"; call create_engine().
    # Expected: result.echo is False
    # ------------------------------------------------------------------
    def test_echo_false_in_production(self):
        from app.config import settings
        with patch.object(settings, "ENV", "production"):
            result = create_engine()
            assert result.echo is False

    # ------------------------------------------------------------------
    # Test 5 – pool_pre_ping is enabled
    # Name: pool_pre_ping enabled
    # Description: pool_pre_ping=True prevents stale connections being used.
    # Steps: Call create_engine(); check pool._pre_ping.
    # Expected: engine.pool._pre_ping is True
    # ------------------------------------------------------------------
    def test_pool_pre_ping_enabled(self):
        result = create_engine()
        assert result.pool._pre_ping is True

    # ------------------------------------------------------------------
    # Test 6 – dialect is set
    # Name: Engine has a dialect
    # Description: A valid engine should always have a dialect configured.
    # Steps: Call create_engine(); check engine.dialect.
    # Expected: result.dialect is not None
    # ------------------------------------------------------------------
    def test_has_dialect(self):
        result = create_engine()
        assert result.dialect is not None


# ===========================================================================
# create_session_factory()
# ===========================================================================

class TestCreateSessionFactory:

    @pytest.fixture
    def factory(self):
        return create_session_factory(engine)

    # ------------------------------------------------------------------
    # Test 7 – Returns async_sessionmaker
    # Name: create_session_factory returns async_sessionmaker
    # Description: The factory should be an async_sessionmaker instance.
    # Steps: Call create_session_factory(engine); check type.
    # Expected: isinstance(result, async_sessionmaker) is True
    # ------------------------------------------------------------------
    def test_returns_async_sessionmaker(self, factory):
        assert isinstance(factory, async_sessionmaker)

    # ------------------------------------------------------------------
    # Test 8 – expire_on_commit is False
    # Name: expire_on_commit=False
    # Description: Objects should not expire after commit in async context.
    # Steps: Check factory.kw["expire_on_commit"].
    # Expected: False
    # ------------------------------------------------------------------
    def test_expire_on_commit_is_false(self, factory):
        assert factory.kw.get("expire_on_commit") is False

    # ------------------------------------------------------------------
    # Test 9 – autoflush is False
    # Name: autoflush=False
    # Description: autoflush should be disabled for explicit flush control.
    # Steps: Check factory.kw["autoflush"].
    # Expected: False
    # ------------------------------------------------------------------
    def test_autoflush_is_false(self, factory):
        assert factory.kw.get("autoflush") is False

    # ------------------------------------------------------------------
    # Test 10 – Session class is AsyncSession
    # Name: Session class is AsyncSession
    # Description: The factory should produce AsyncSession instances.
    # Steps: Check factory.class_.
    # Expected: factory.class_ is AsyncSession
    # ------------------------------------------------------------------
    def test_session_class_is_async_session(self, factory):
        assert factory.class_ is AsyncSession

    # ------------------------------------------------------------------
    # Test 11 – Factory is bound to the supplied engine
    # Name: Factory bound to engine
    # Description: The factory should be bound to whichever engine is passed in.
    # Steps: Check factory.kw["bind"].
    # Expected: factory.kw["bind"] is engine
    # ------------------------------------------------------------------
    def test_bound_to_supplied_engine(self, factory):
        assert factory.kw.get("bind") is engine


# ===========================================================================
# Module-level singletons
# ===========================================================================

class TestModuleSingletons:

    # ------------------------------------------------------------------
    # Test 12 – Module engine is AsyncEngine
    # Name: Module-level engine type
    # Description: The module-level engine singleton should be an AsyncEngine.
    # Steps: Import engine; check type.
    # Expected: isinstance(engine, AsyncEngine) is True
    # ------------------------------------------------------------------
    def test_engine_is_async_engine(self):
        assert isinstance(engine, AsyncEngine)

    # ------------------------------------------------------------------
    # Test 13 – Module AsyncSessionLocal is async_sessionmaker
    # Name: Module-level session factory type
    # Description: The module-level AsyncSessionLocal should be an async_sessionmaker.
    # Steps: Import AsyncSessionLocal; check type.
    # Expected: isinstance(AsyncSessionLocal, async_sessionmaker) is True
    # ------------------------------------------------------------------
    def test_async_session_local_is_async_sessionmaker(self):
        assert isinstance(AsyncSessionLocal, async_sessionmaker)

    # ------------------------------------------------------------------
    # Test 14 – AsyncSessionLocal is bound to module engine
    # Name: Module session factory bound to module engine
    # Description: The module-level factory should reference the module-level engine.
    # Steps: Check AsyncSessionLocal.kw["bind"] is engine.
    # Expected: True
    # ------------------------------------------------------------------
    def test_session_local_bound_to_module_engine(self):
        assert AsyncSessionLocal.kw.get("bind") is engine


# ===========================================================================
# get_db()
# ===========================================================================

class TestGetDb:

    # ------------------------------------------------------------------
    # Test 15 – get_db is an async generator function
    # Name: get_db is async generator
    # Description: get_db must be an async generator, not a plain coroutine.
    # Steps: Check inspect.isasyncgenfunction(get_db).
    # Expected: True
    # ------------------------------------------------------------------
    def test_is_async_generator_function(self):
        assert inspect.isasyncgenfunction(get_db)

    # ------------------------------------------------------------------
    # Test 16 – get_db yields an AsyncSession
    # Name: get_db yields AsyncSession
    # Description: The first value yielded should be an AsyncSession.
    # Steps: Patch AsyncSessionLocal; advance generator one step.
    # Expected: Yielded value is the mocked session.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_yields_async_session(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_session

    # ------------------------------------------------------------------
    # Test 17 – get_db yields exactly once
    # Name: get_db yields exactly one session
    # Description: The generator should stop after the first yield.
    # Steps: Iterate get_db() fully; count yielded values.
    # Expected: Exactly one item yielded.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_yields_exactly_once(self):
        mock_session, mock_cm = make_mock_session()
        yielded = []
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            async for session in get_db():
                yielded.append(session)
        assert len(yielded) == 1
        assert yielded[0] is mock_session

    # ------------------------------------------------------------------
    # Test 18 – get_db closes session after use
    # Name: Session closed on normal exit
    # Description: __aexit__ should be called once the generator is exhausted.
    # Steps: Exhaust the generator; verify __aexit__ was called once.
    # Expected: mock_cm.__aexit__ called exactly once.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_closes_session_after_yield(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            gen = get_db()
            await gen.__anext__()
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
        mock_cm.__aexit__.assert_called_once()

    # ------------------------------------------------------------------
    # Test 19 – get_db rolls back on SQLAlchemyError
    # Name: Rollback on SQLAlchemyError
    # Description: If a SQLAlchemyError is thrown into the generator,
    #              the session should be rolled back before re-raising.
    # Steps: Throw SQLAlchemyError into the generator; verify rollback called.
    # Expected: session.rollback() called once; error re-raised.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_rolls_back_on_sqlalchemy_error(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(SQLAlchemyError):
                await gen.athrow(SQLAlchemyError("db error"))
        mock_session.rollback.assert_called_once()

    # ------------------------------------------------------------------
    # Test 20 – get_db rolls back on unexpected Exception
    # Name: Rollback on unexpected Exception
    # Description: If any non-SQLAlchemy exception is thrown,
    #              the session should still be rolled back.
    # Steps: Throw a RuntimeError into the generator; verify rollback called.
    # Expected: session.rollback() called once; RuntimeError re-raised.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_rolls_back_on_unexpected_exception(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(RuntimeError):
                await gen.athrow(RuntimeError("unexpected"))
        mock_session.rollback.assert_called_once()

    # ------------------------------------------------------------------
    # Test 21 – get_db re-raises SQLAlchemyError after rollback
    # Name: SQLAlchemyError is re-raised
    # Description: After rolling back, the original error must propagate.
    # Steps: Throw SQLAlchemyError; confirm it is re-raised.
    # Expected: SQLAlchemyError propagates to caller.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_reraises_sqlalchemy_error(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(SQLAlchemyError, match="db error"):
                await gen.athrow(SQLAlchemyError("db error"))

    # ------------------------------------------------------------------
    # Test 22 – get_db logs SQLAlchemyError
    # Name: SQLAlchemyError is logged
    # Description: A database error should be logged via logger.exception.
    # Steps: Throw SQLAlchemyError; verify logger.exception was called.
    # Expected: logger.exception called once.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_logs_sqlalchemy_error(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            with patch(f"{MODULE}.logger") as mock_logger:
                gen = get_db()
                await gen.__anext__()
                with pytest.raises(SQLAlchemyError):
                    await gen.athrow(SQLAlchemyError("db error"))
        mock_logger.exception.assert_called_once()

    # ------------------------------------------------------------------
    # Test 23 – get_db logs unexpected Exception
    # Name: Unexpected exception is logged
    # Description: A non-SQLAlchemy error should also be logged.
    # Steps: Throw RuntimeError; verify logger.exception was called.
    # Expected: logger.exception called once.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_logs_unexpected_exception(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            with patch(f"{MODULE}.logger") as mock_logger:
                gen = get_db()
                await gen.__anext__()
                with pytest.raises(RuntimeError):
                    await gen.athrow(RuntimeError("unexpected"))
        mock_logger.exception.assert_called_once()

    # ------------------------------------------------------------------
    # Test 24 – get_db closes session even on error
    # Name: Session closed on error
    # Description: __aexit__ must be called regardless of whether an
    #              exception was raised.
    # Steps: Throw an error; verify __aexit__ was still called.
    # Expected: mock_cm.__aexit__ called once.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_closes_session_on_error(self):
        mock_session, mock_cm = make_mock_session()
        with patch(f"{MODULE}.AsyncSessionLocal", return_value=mock_cm):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(SQLAlchemyError):
                await gen.athrow(SQLAlchemyError("db error"))
        mock_cm.__aexit__.assert_called_once()


# ===========================================================================
# get_conn()
# ===========================================================================

class TestGetConn:

    # ------------------------------------------------------------------
    # Test 25 – get_conn is an async generator function
    # Name: get_conn is async generator
    # Description: get_conn must be an async generator function.
    # Steps: Check inspect.isasyncgenfunction(get_conn).
    # Expected: True
    # ------------------------------------------------------------------
    def test_is_async_generator_function(self):
        assert inspect.isasyncgenfunction(get_conn)

    # ------------------------------------------------------------------
    # Test 26 – get_conn yields an AsyncConnection
    # Name: get_conn yields AsyncConnection
    # Description: The value yielded should be an AsyncConnection.
    # Steps: Patch engine.begin(); advance generator one step.
    # Expected: Yielded value is the mocked connection.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_yields_async_connection(self):
        mock_conn, mock_cm = make_mock_conn()
        with patch(f"{MODULE}.engine") as mock_engine:
            mock_engine.begin.return_value = mock_cm
            gen = get_conn()
            conn = await gen.__anext__()
            assert conn is mock_conn

    # ------------------------------------------------------------------
    # Test 27 – get_conn yields exactly once
    # Name: get_conn yields exactly one connection
    # Description: The generator should stop after the first yield.
    # Steps: Iterate get_conn() fully; count yielded values.
    # Expected: Exactly one item yielded.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_yields_exactly_once(self):
        mock_conn, mock_cm = make_mock_conn()
        yielded = []
        with patch(f"{MODULE}.engine") as mock_engine:
            mock_engine.begin.return_value = mock_cm
            async for conn in get_conn():
                yielded.append(conn)
        assert len(yielded) == 1
        assert yielded[0] is mock_conn

    # ------------------------------------------------------------------
    # Test 28 – get_conn logs SQLAlchemyError
    # Name: Connection error is logged
    # Description: A SQLAlchemyError from engine.begin() should be logged.
    # Steps: Patch engine.begin() to raise; verify logger.exception called.
    # Expected: logger.exception called once; error re-raised.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_logs_and_reraises_sqlalchemy_error(self):
        with patch(f"{MODULE}.engine") as mock_engine:
            mock_engine.begin.side_effect = SQLAlchemyError("conn error")
            with patch(f"{MODULE}.logger") as mock_logger:
                with pytest.raises(SQLAlchemyError, match="conn error"):
                    async for _ in get_conn():
                        pass
        mock_logger.exception.assert_called_once()


# ===========================================================================
# dispose_engine()
# ===========================================================================

class TestDisposeEngine:

    # ------------------------------------------------------------------
    # Test 29 – dispose_engine calls engine.dispose()
    # Name: dispose_engine disposes pool
    # Description: dispose_engine() should call engine.dispose() once.
    # Steps: Patch engine.dispose(); call dispose_engine().
    # Expected: engine.dispose() called exactly once.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_calls_engine_dispose(self):
        with patch(f"{MODULE}.engine") as mock_engine:
            mock_engine.dispose = AsyncMock()
            await dispose_engine()
        mock_engine.dispose.assert_called_once()

    # ------------------------------------------------------------------
    # Test 30 – dispose_engine logs success
    # Name: Successful disposal is logged
    # Description: A successful dispose should log an info message.
    # Steps: Patch engine.dispose(); call dispose_engine(); check logger.
    # Expected: logger.info called once.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_logs_success(self):
        with patch(f"{MODULE}.engine") as mock_engine:
            mock_engine.dispose = AsyncMock()
            with patch(f"{MODULE}.logger") as mock_logger:
                await dispose_engine()
        mock_logger.info.assert_called_once()

    # ------------------------------------------------------------------
    # Test 31 – dispose_engine logs and re-raises SQLAlchemyError
    # Name: Disposal error is logged and re-raised
    # Description: If engine.dispose() raises, the error should be logged
    #              and re-raised so the caller knows shutdown failed.
    # Steps: Patch engine.dispose() to raise; call dispose_engine().
    # Expected: logger.exception called; SQLAlchemyError re-raised.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_logs_and_reraises_on_error(self):
        with patch(f"{MODULE}.engine") as mock_engine:
            mock_engine.dispose = AsyncMock(side_effect=SQLAlchemyError("dispose error"))
            with patch(f"{MODULE}.logger") as mock_logger:
                with pytest.raises(SQLAlchemyError, match="dispose error"):
                    await dispose_engine()
        mock_logger.exception.assert_called_once()

    # ------------------------------------------------------------------
    # Test 32 – dispose_engine does not log success on error
    # Name: Info not logged when disposal fails
    # Description: logger.info should not be called if an error is raised.
    # Steps: Patch engine.dispose() to raise; verify logger.info not called.
    # Expected: logger.info never called.
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_does_not_log_success_on_error(self):
        with patch(f"{MODULE}.engine") as mock_engine:
            mock_engine.dispose = AsyncMock(side_effect=SQLAlchemyError("dispose error"))
            with patch(f"{MODULE}.logger") as mock_logger:
                with pytest.raises(SQLAlchemyError):
                    await dispose_engine()
        mock_logger.info.assert_not_called()
