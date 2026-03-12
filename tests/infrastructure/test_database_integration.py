import json
import pytest
from sqlalchemy import text
from loguru import logger

pytestmark = pytest.mark.asyncio(loop_scope="module")
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.models import Auction
from app.infrastructure.database import (
    create_engine,
    create_session_factory,
    dispose_engine,
    get_conn,
    get_db,
)
from app.utils.exceptions import DatabaseError


@pytest.mark.integration
class TestAuctionQueriesIntegration:

    async def test_select_all_auctions(self):
        gen = get_db()
        session = await gen.asend(None)
        result = await session.exec(select(Auction))
        auctions = result.all()
        assert isinstance(auctions, list)
        assert len(auctions) == 149
        await gen.aclose()


@pytest.mark.integration
class TestCreateEngineIntegration:

    async def test_engine_can_connect(self):
        engine = create_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    async def test_session_factory_yields_working_session(self):
        engine = create_engine()
        factory = create_session_factory(engine)
        async with factory() as session:
            result = await session.exec(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()


@pytest.mark.integration
class TestGetDbIntegration:

    async def test_yields_usable_session(self):
        gen = get_db()
        session = await gen.asend(None)
        assert isinstance(session, AsyncSession)
        result = await session.exec(text("SELECT 1"))
        assert result.scalar() == 1
        await gen.aclose()

    async def test_rolls_back_on_sqlalchemy_error(self):
        gen = get_db()
        await gen.asend(None)
        with pytest.raises(DatabaseError):
            await gen.athrow(SQLAlchemyError("forced rollback"))

    async def test_rolls_back_on_generic_exception(self):
        gen = get_db()
        await gen.asend(None)
        with pytest.raises(DatabaseError):
            await gen.athrow(RuntimeError("forced rollback"))

    async def test_reraises_sqlalchemy_error(self):
        error = SQLAlchemyError("forced")
        gen = get_db()
        await gen.asend(None)
        with pytest.raises(DatabaseError) as exc_info:
            await gen.athrow(error)
        assert isinstance(exc_info.value.__cause__, SQLAlchemyError)

    async def test_reraises_generic_exception(self):
        error = RuntimeError("forced")
        gen = get_db()
        await gen.asend(None)
        with pytest.raises(DatabaseError) as exc_info:
            await gen.athrow(error)
        assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.integration
class TestGetConnIntegration:

    async def test_yields_usable_connection(self):
        gen = get_conn()
        conn = await gen.asend(None)
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
        await gen.aclose()

    async def test_reraises_sqlalchemy_error(self):
        error = SQLAlchemyError("forced")
        gen = get_conn()
        await gen.asend(None)
        with pytest.raises(DatabaseError) as exc_info:
            await gen.athrow(error)
        assert isinstance(exc_info.value.__cause__, SQLAlchemyError)


@pytest.mark.integration
class TestDisposeEngineIntegration:

    async def test_dispose_does_not_raise(self):
        await dispose_engine()

    async def test_connections_still_work_after_dispose(self):
        await dispose_engine()
        gen = get_db()
        session = await gen.asend(None)
        result = await session.exec(text("SELECT 1"))
        assert result.scalar() == 1
        await gen.aclose()
