from dataclasses import dataclass
from loguru import logger
from app.domain.models.report import Report
from app.domain.models.schemas import ReportDetail
from app.utils.exceptions import TransformerError


@dataclass
class WeightBin:
    min_weight: int
    max_weight: int
    weight_class: int


class ReportTransformer:
    _WEIGHT_BINS = [
        WeightBin(700, 749, 1),
        WeightBin(750, 799, 2),
        WeightBin(800, 849, 3),
        WeightBin(850, 899, 4),
    ]

    def transform(self, details: list[ReportDetail], auction_slug: str) -> list[Report]:
        try:
            logger.debug(
                "Transform started",
                event="transform_start",
                operation="transform_report_details",
                slug=auction_slug,
                detail_count=len(details),
            )
            groups = self._group_by_fields(details)

            reports = []
            for (report_date, region), group in groups.items():
                first = group[0]
                kwargs: dict = {
                    "report_date": report_date,
                    "region": region,
                    "auction_slug": auction_slug,
                    **self._create_report_header(first),
                    **self._aggregate_bins(group),
                }
                reports.append(Report(**kwargs))

            logger.debug(
                "Transform completed",
                event="transform_complete",
                operation="transform_report_details",
                slug=auction_slug,
                group_count=len(groups),
                report_count=len(reports),
            )
            return reports
        except Exception as err:
            logger.exception(
                "Transform failed",
                event="transform_failed",
                operation="transform_report_details",
                slug=auction_slug,
                error=str(err),
                error_type=type(err).__name__,
            )
            raise TransformerError("An error occurred during data transformation") from err
    
    def _aggregate_bins(self, group: list[ReportDetail]) -> dict:
        kwargs = {}
        for bin_ in self._WEIGHT_BINS:
            binned = [
                d for d in group
                if bin_.min_weight <= d.avg_weight <= bin_.max_weight
            ]
            head, weight, price = self._aggregate(binned)
            wc = bin_.weight_class
            kwargs[f"head{wc}"] = head
            kwargs[f"weight{wc}"] = weight
            kwargs[f"price{wc}"] = price

        # Class 5 is the total across all items in the group
        head5, weight5, price5 = self._aggregate(group)
        kwargs["head5"] = head5
        kwargs["weight5"] = weight5
        kwargs["price5"] = price5

        return kwargs
    
    @staticmethod
    def _group_by_fields(details: list[ReportDetail]) -> dict[tuple, list[ReportDetail]]:
        groups: dict[tuple, list[ReportDetail]] = {}
        for detail in details:
            key = (detail.report_date, detail.region)
            groups.setdefault(key, []).append(detail)
        return groups
    
    @staticmethod
    def _create_report_header(detail: ReportDetail) -> dict:
        return {
            "report_end_date": detail.report_end_date,
            "published_date": detail.published_date,
            "report_status": detail.report_status,
        }

    @staticmethod
    def _aggregate(details: list[ReportDetail]) -> tuple[int, float, float]:
        head = sum(d.head_count for d in details)
        if head == 0:
            return 0, 0.0, 0.0
        weight = sum(d.head_count * d.avg_weight for d in details) / head
        price = sum(d.head_count * d.avg_price for d in details) / head
        return head, weight, price
