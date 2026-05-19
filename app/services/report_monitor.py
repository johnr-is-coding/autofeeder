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

        
_REPORT_UPDATE_COLS = [
    "report_end_date", "published_date", "report_status",
    "head1", "weight1", "price1",
    "head2", "weight2", "price2",
    "head3", "weight3", "price3",
    "head4", "weight4", "price4",
    "head5", "weight5", "price5",
]

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
            if isinstance(reports, BaseException):
                logger.error(
                    "Error generating reports",
                    event="generate_reports_exception",
                    operation="run_cycle",
                    slug=change.slug,
                    error=str(reports),
                    error_type=type(reports).__name__,
                )
                failed_slugs.append(change.slug)
                continue

            try:
                if not reports:
                    logger.debug(
                        "No reports generated for slug",
                        event="generate_reports_empty",
                        operation="run_cycle",
                        slug=change.slug,
                    )
                await self._persist_report_update(reports, change.incoming)
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

        if failed_slugs:
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

    def _get_changes(
            self, 
            stored_reports: list[StoredReport], 
            incoming_map: dict[str, IncomingReport]
    ) -> list[ReportChange]:
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
            started_at = perf_counter()
            logger.debug(
                "Generating reports for slug",
                event="generate_reports_start",
                operation="generate_reports",
                slug=slug,
                market_type=market_type.value,
            )
            data = await self.api_client.fetch_report_details(slug, market_type)
            reports = self.transformer.transform(data.results, slug)
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.debug(
                "Generated reports for slug",
                event="generate_reports_complete",
                operation="generate_reports",
                slug=slug,
                market_type=market_type.value,
                generated_count=len(reports),
                elapsed_ms=elapsed_ms,
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

    async def _persist_report_update(self, reports: list[Report], incoming: IncomingReport) -> None:
        """Upsert reports and the stored report in a single transaction"""
        try:
            started_at = perf_counter()

            rows =[r.model_dump() for r in reports]
            report_stmt = pg_insert(Report).values(rows)
            report_stmt = report_stmt.on_conflict_do_update(
                constraint="uq_report_slug_date_region",
                set_={col: report_stmt.excluded[col] for col in _REPORT_UPDATE_COLS},
            )
            await self.session.execute(report_stmt)

            stored_data = {
                "slug": incoming.slug,
                "report_date": incoming.report_date,
                "published_date": incoming.published_date,
                "report_status": incoming.report_status,
                "market_type": incoming.market_type,
                "has_corrections": incoming.has_corrections,
            }
            stored_stmt = pg_insert(StoredReport).values(stored_data)
            stored_stmt = stored_stmt.on_conflict_do_update(
                index_elements=["slug"],
                set_={k: stored_stmt.excluded[k] for k in stored_data if k != "slug"},
            )
            await self.session.execute(stored_stmt)

            await self.session.commit()
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.debug(
                "Persisted report updates",
                event="db_persist_report_updates_complete",
                operation="_persist_report_update",
                slug=incoming.slug,
                row_count=len(reports),
                elapsed_ms=elapsed_ms,
            )
        except SQLAlchemyError as err:
            await self.session.rollback()
            logger.exception(
                "Failed to persist report update",
                event="db_persist_report_update_failed",
                operation="_persist_report_update",
                slug=incoming.slug,
                row_count=len(reports),
                error=str(err),
                error_type=type(err).__name__,
            )
            raise DatabaseError(f"Failed to persist report update") from err

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
