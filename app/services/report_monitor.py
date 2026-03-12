import asyncio
from dataclasses import dataclass
from time import perf_counter

from loguru import logger
from tqdm import tqdm
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defaultload

from app.domain.models.report import Report
from app.domain.models.auction import Auction
from app.domain.models.schemas import IncomingReport
from app.domain.models.stored_report import StoredReport
from app.infrastructure.api_client import APIClient
from app.infrastructure.transformers import ReportTransformer
from app.utils.enums import MarketType
from app.utils.exceptions import APIClientError, DatabaseError, ServiceError, TransformerError


@dataclass
class ReportChange:
    slug: str
    stored: StoredReport
    incoming: IncomingReport


class ReportMonitor:

    def __init__(self, api_client: APIClient, session: AsyncSession) -> None:
        self.api_client = api_client
        self.session = session
        self.transformer = ReportTransformer()

    async def run_cycle(self) -> None:
        try:
            incoming_map = await self.api_client.fetch_current_reports()
            stored_reports = await self._load_stored_reports()
            logger.debug(
                "Loaded monitoring inputs",
                event="monitor_inputs_loaded",
                operation="run_cycle",
                incoming_count=len(incoming_map),
                stored_count=len(stored_reports),
            )
        except (APIClientError, DatabaseError) as err:
            logger.exception(
                "Failed to initialize monitoring cycle",
                event="monitor_init_failed",
                operation="run_cycle",
                error=str(err),
                error_type=type(err).__name__,
            )
            raise ServiceError("Failed to initialize report monitoring cycle") from err

        changes = self._get_changes(stored_reports, incoming_map)
        if not changes:
            logger.info("No report changes detected")
            return
        logger.info(
            "Report changes detected",
            event="report_changes_detected",
            operation="run_cycle",
            change_count=len(changes),
        )

        fetched = await asyncio.gather(
            *[self._generate_reports(change.slug, change.stored.market_type) for change in changes],
            return_exceptions=True,
        )

        failed_slugs: list[str] = []
        for change, reports in tqdm(zip(changes, fetched), total=len(changes), desc="Processing report changes"):
            if isinstance(reports, Exception):
                logger.error("Error generating reports", slug=change.slug, error=str(reports))
                failed_slugs.append(change.slug)
                continue

            try:
                await self._upsert_reports(reports)
                await self._upsert_stored_report(change.incoming)
                logger.info("Updated report and stored report", slug=change.slug)
            except DatabaseError as err:
                logger.error(
                    "Failed to persist report updates",
                    event="report_persist_failed",
                    operation="run_cycle",
                    slug=change.slug,
                    error=str(err),
                    error_type=type(err).__name__,
                )
                failed_slugs.append(change.slug)
                continue

        if failed_slugs:
            # Fail the cycle explicitly so upstream error boundaries can apply retry policy.
            logger.warning(
                "Cycle completed with failed slugs",
                event="run_cycle_partial_failure",
                operation="run_cycle",
                failed_slug_count=len(failed_slugs),
                failed_slugs=failed_slugs,
            )
            raise ServiceError(f"Cycle completed with failed report updates for slugs: {failed_slugs}")

        logger.info(
            "Cycle completed successfully",
            event="run_cycle_success",
            operation="run_cycle",
            processed_changes=len(changes),
        )

    def _get_changes(self, stored_reports: list[StoredReport], incoming_map: dict[str, IncomingReport]) -> list[ReportChange]:
        changes = []
        for stored in stored_reports:
            incoming = incoming_map.get(stored.slug)
            if incoming is None:
                continue
            
            if self._detect_changes(stored, incoming):
                changes.append(ReportChange(stored.slug, stored, incoming))
        
        return changes

    async def _generate_reports(self, slug: str, market_type: MarketType) -> list[Report]:
        try:
            logger.debug(
                "Generating reports for slug",
                event="generate_reports_start",
                operation="generate_reports",
                slug=slug,
                market_type=market_type.value,
            )
            data = await self.api_client.fetch_report_details(slug, market_type)
            reports = self.transformer.transform(data.results, slug)
            logger.debug(
                "Generated reports for slug",
                event="generate_reports_complete",
                operation="generate_reports",
                slug=slug,
                market_type=market_type.value,
                generated_count=len(reports),
            )
            return reports
        except (APIClientError, TransformerError) as err:
            logger.exception(
                "Failed to generate reports",
                event="generate_reports_failed",
                operation="generate_reports",
                slug=slug,
                market_type=market_type.value,
                error=str(err),
                error_type=type(err).__name__,
            )
            raise ServiceError(f"Failed to generate reports for {slug!r}") from err
    
    @staticmethod
    def _detect_changes(stored: StoredReport, incoming: IncomingReport) -> bool:
        return (
            incoming.report_date != stored.report_date or
            incoming.report_status != stored.report_status or
            incoming.published_date != stored.published_date
        )
        
        
    _REPORT_UPDATE_COLS = [
        "report_end_date", "published_date", "report_status",
        "head1", "weight1", "price1",
        "head2", "weight2", "price2",
        "head3", "weight3", "price3",
        "head4", "weight4", "price4",
        "head5", "weight5", "price5",
    ]

    async def _upsert_reports(self, reports: list[Report]) -> None:
        try:
            started_at = perf_counter()
            rows = [r.model_dump(exclude={"auction"}) for r in reports]
            stmt = pg_insert(Report).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_report_slug_date_region",
                set_={col: stmt.excluded[col] for col in self._REPORT_UPDATE_COLS},
            )
            await self.session.execute(stmt)
            await self.session.commit()
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.debug(
                "Upserted report rows",
                event="db_upsert_reports_complete",
                operation="upsert_reports",
                row_count=len(rows),
                elapsed_ms=elapsed_ms,
            )
        except SQLAlchemyError as err:
            await self.session.rollback()
            logger.exception(
                "Report upsert failed",
                event="db_upsert_reports_failed",
                operation="upsert_reports",
                row_count=len(reports),
                error=str(err),
                error_type=type(err).__name__,
            )
            raise DatabaseError("Failed to upsert report rows") from err


    async def _upsert_stored_report(self, incoming: IncomingReport) -> None:
        try:
            started_at = perf_counter()
            data = {
                "slug": incoming.slug,
                "report_date": incoming.report_date,
                "published_date": incoming.published_date,
                "report_status": incoming.report_status,
                "market_type": incoming.market_type,
                "has_corrections": incoming.has_corrections,
            }
            stmt = pg_insert(StoredReport).values(data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["slug"],
                set_={k: stmt.excluded[k] for k in data if k != "slug"},
            )
            await self.session.execute(stmt)
            await self.session.commit()
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.debug(
                "Upserted stored report row",
                event="db_upsert_stored_report_complete",
                operation="upsert_stored_report",
                slug=incoming.slug,
                elapsed_ms=elapsed_ms,
            )
        except SQLAlchemyError as err:
            await self.session.rollback()
            logger.exception(
                "Stored report upsert failed",
                event="db_upsert_stored_report_failed",
                operation="upsert_stored_report",
                slug=incoming.slug,
                error=str(err),
                error_type=type(err).__name__,
            )
            raise DatabaseError("Failed to upsert stored report row") from err


    async def _load_stored_reports(self) -> list[StoredReport]:
        try:
            started_at = perf_counter()
            result = await self.session.execute(
                select(StoredReport).options(
                    defaultload(StoredReport.auction).noload(Auction.reports)
                )
            )
            stored_reports = result.unique().scalars().all()
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.debug(
                "Loaded stored reports",
                event="db_load_stored_reports_complete",
                operation="load_stored_reports",
                row_count=len(stored_reports),
                elapsed_ms=elapsed_ms,
            )
            return stored_reports
        except SQLAlchemyError as err:
            logger.exception(
                "Failed to load stored reports",
                event="db_load_stored_reports_failed",
                operation="load_stored_reports",
                error=str(err),
                error_type=type(err).__name__,
            )
            raise DatabaseError("Failed to load stored reports") from err
