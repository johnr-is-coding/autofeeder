from dataclasses import dataclass
from enum import Enum

from loguru import logger
from sqlalchemy import select
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
from app.utils.exceptions import APIClientError


class ReportChangeType(Enum):
    NEW_REPORT_DATE = "new_report_date"
    PUBLISHED_DATE_UPDATED = "published_date_updated"
    STATUS_CHANGED = "status_changed"


@dataclass
class ReportChange:
    slug: str
    change_type: ReportChangeType
    stored: StoredReport
    incoming: IncomingReport


class ReportMonitor:

    def __init__(self, api_client: APIClient, session: AsyncSession) -> None:
        self.api_client = api_client
        self.session = session
        self.transformer = ReportTransformer()

    async def run_cycle(self) -> None:
        incoming_map = await self.api_client.fetch_current_reports()
        stored_reports = await self._load_stored_reports()

        for stored in stored_reports:
            incoming = incoming_map.get(stored.slug)
            if incoming is None:
                logger.debug("Skipping untracked report slug", slug=stored.slug)
                continue

            changes = self._detect_changes(stored, incoming)
            for change in changes:
                await self._dispatch(change)


    def _detect_changes(self, stored: StoredReport, incoming: IncomingReport) -> list[ReportChange]:
        """
        Detect a single change between the stored and incoming report.

        Priority order (only the highest-priority change is returned):
          1. report_date changed    → NEW_REPORT_DATE
          2. report_status changed  → STATUS_CHANGED
          3. published_date changed → PUBLISHED_DATE_UPDATED
        """
        
        if incoming.report_date != stored.report_date:
            return [ReportChange(stored.slug, ReportChangeType.NEW_REPORT_DATE, stored, incoming)]
        if incoming.report_status != stored.report_status:
            return [ReportChange(stored.slug, ReportChangeType.STATUS_CHANGED, stored, incoming)]
        if incoming.published_date != stored.published_date:
            return [ReportChange(stored.slug, ReportChangeType.PUBLISHED_DATE_UPDATED, stored, incoming)]
        return []


    async def _dispatch(self, change: ReportChange) -> None:
        handlers = {
            ReportChangeType.NEW_REPORT_DATE: self._on_new_report_date,
            ReportChangeType.PUBLISHED_DATE_UPDATED: self._on_published_date_updated,
            ReportChangeType.STATUS_CHANGED: self._on_status_changed,
        }
        logger.info(
            "Report change detected",
            slug=change.slug,
            change=change.change_type.value,
            stored_report_date=str(change.stored.report_date),
            incoming_report_date=str(change.incoming.report_date),
        )
        await handlers[change.change_type](change)


    # ------------------------------------------------------------------
    # Handlers — implement each scenario here
    # ------------------------------------------------------------------

    async def _on_new_report_date(self, change: ReportChange) -> None:
        """
        Triggered when report_date changes — a new reporting period is available.

        change.stored   → the last known LatestReport (prev report_date, market_type, etc.)
        change.incoming → the new LatestReport from the API

        Expected actions:
          - Fetch fresh detail rows:
              api_client.fetch_report_details(slug, market_type, prev_report_date)
          - Build and insert a new Reports record from the ReportResponse
          - Upsert the LatestReport in the DB to reflect change.incoming
        """
        
        reports = await self._generate_reports(
            change.stored.slug,
            change.stored.market_type,
            change.stored.report_date,
        )
        if reports:
            await self._upsert_reports(reports)
        await self._upsert_stored_report(change.incoming)


    async def _on_status_changed(self, change: ReportChange) -> None:
        """
        Triggered when report_status changes (e.g. preliminary → final),
        while report_date and published_date remain the same.

        change.stored.report_status   → old status
        change.incoming.report_status → new status

        Expected actions:
          - Update LatestReport.report_status in DB
          - Optionally re-fetch and update Reports details if final data differs from preliminary
        """
        
        reports = await self._generate_reports(
            change.stored.slug,
            change.stored.market_type,
            change.stored.report_date,
        )
        if reports:
            await self._upsert_reports(reports)
        await self._upsert_stored_report(change.incoming)


    async def _on_published_date_updated(self, change: ReportChange) -> None:
        """
        Triggered when published_date changes but report_date stays the same.
        Corrections have been re-published for the current reporting period.

        change.stored   → stored LatestReport (same report_date, old published_date)
        change.incoming → incoming LatestReport (same report_date, new published_date)

        Expected actions:
          - Re-fetch report details for the same report_date
          - Update the existing Reports record(s) with the corrected data
          - Update LatestReport.published_date in DB
        """

        logger.info(
            "Report published date updated",
            slug=change.slug,
            from_published_date=str(change.stored.published_date),
            to_published_date=str(change.incoming.published_date),
        )
        reports = await self._generate_reports(
            change.stored.slug,
            change.stored.market_type,
            change.stored.report_date,
        )
        if reports:
            await self._upsert_reports(reports)
        await self._upsert_stored_report(change.incoming)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _generate_reports(self, auction_slug: str, market_type: MarketType ,report_date: str) -> list[Report] | None:
        try:
            data = await self.api_client.fetch_report_details(auction_slug, market_type, report_date)
            if data is None:
                return None
            return self.transformer.transform(data.results, auction_slug)
        
        except APIClientError as err:
            logger.error("Failed to generate reports", slug=auction_slug, report_date=report_date, error=str(err))
            return None
        
        
    _REPORT_UPDATE_COLS = [
        "report_end_date", "published_date", "report_status",
        "head1", "weight1", "price1",
        "head2", "weight2", "price2",
        "head3", "weight3", "price3",
        "head4", "weight4", "price4",
        "head5", "weight5", "price5",
    ]

    async def _upsert_reports(self, reports: list[Report]) -> None:
        rows = [r.model_dump(exclude={"auction"}) for r in reports]
        stmt = pg_insert(Report).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["auction_slug", "report_date", "region"],
            set_={col: stmt.excluded[col] for col in self._REPORT_UPDATE_COLS},
        )
        await self.session.execute(stmt)
        await self.session.commit()


    async def _upsert_stored_report(self, incoming: IncomingReport) -> None:
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


    async def _load_stored_reports(self) -> list[StoredReport]:
        result = await self.session.execute(
            select(StoredReport).options(
                defaultload(StoredReport.auction).noload(Auction.reports)
            )
        )
        return result.unique().scalars().all()
