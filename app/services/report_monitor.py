from dataclasses import dataclass
from enum import Enum

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import IncomingReport, StoredReport
from app.infrastructure.api_client import APIClient


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

    async def run_cycle(self) -> None:
        incoming_reports = await self.api_client.fetch_current_reports()
        stored_map = await self._load_stored_reports()

        for incoming in incoming_reports:
            stored = stored_map.get(incoming.slug)
            if stored is None:
                logger.debug("Skipping untracked report slug", slug=incoming.slug)
                continue

            changes = self._detect_changes(stored, incoming)
            for change in changes:
                await self._dispatch(change)

    def _detect_changes(self, stored: StoredReport, incoming: IncomingReport) -> list[ReportChange]:
        """
        Detect field-level changes between the stored and incoming LatestReport.

        Priority order (avoids duplicate events on the same cycle):
          1. report_date changed    → NEW_REPORT_DATE (new reporting period; implies a new
                                      published_date too, so we don't fire PUBLISHED_DATE_UPDATED)
          2. published_date changed → PUBLISHED_DATE_UPDATED (correction to the existing period)
          3. report_status changed  → STATUS_CHANGED (e.g. preliminary → final)

        Cases 2 and 3 are not mutually exclusive — a correction could also flip the status.
        """
        if incoming.report_date != stored.report_date:
            return [ReportChange(stored.slug, ReportChangeType.NEW_REPORT_DATE, stored, incoming)]

        changes = []
        if incoming.published_date != stored.published_date:
            changes.append(ReportChange(stored.slug, ReportChangeType.PUBLISHED_DATE_UPDATED, stored, incoming))
        if incoming.report_status != stored.report_status:
            changes.append(ReportChange(stored.slug, ReportChangeType.STATUS_CHANGED, stored, incoming))
        return changes

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
        pass

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
        pass

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
        logger.info(
            "Report status transition",
            slug=change.slug,
            from_status=change.stored.report_status.value,
            to_status=change.incoming.report_status.value,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_stored_reports(self) -> dict[str, StoredReport]:
        result = await self.session.execute(select(StoredReport))
        return {r.slug: r for r in result.scalars().all()}
