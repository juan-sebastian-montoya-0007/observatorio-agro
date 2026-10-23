from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.agriculture import AgricultureRepository, SummaryResult
from app.schemas.agriculture import RankingItemOut, RecordPageOut, SeriesPointOut, SummaryData
from app.schemas.common import (
    AnalyticalResponse,
    AnalyticalWarningOut,
    CoverageEnvelope,
    ResponseMeta,
)
from app.schemas.filters import AgricultureFilters
from app.schemas.records import RecordPageQuery
from app.statistics import AnalyticalWarning, Indicator, comparison_warnings

_METHODOLOGY = [
    (
        "El rendimiento se calcula como la razón entre la suma de producción y la "
        "suma de área cosechada; no se promedian rendimientos reportados."
    ),
    (
        "En modo año agrícola, los semestres disponibles sustituyen al registro anual "
        "equivalente para evitar doble conteo."
    ),
]


def indicator_unit(indicator: Indicator) -> str:
    return {
        Indicator.PLANTED_AREA: "ha",
        Indicator.HARVESTED_AREA: "ha",
        Indicator.PRODUCTION: "t",
        Indicator.YIELD: "t/ha",
    }[indicator]


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.repository = AgricultureRepository(session)

    def records(self, query: RecordPageQuery) -> AnalyticalResponse[RecordPageOut]:
        version = self.repository.latest_published_version()
        summary = self.repository.summary(query)
        result = self.repository.records(query)
        return AnalyticalResponse(
            data=RecordPageOut.model_validate(result, from_attributes=True),
            meta=self._meta(version, query),
            coverage=self._coverage(summary),
            warnings=self._warnings(query, summary.coverage_status, version),
            methodology=[*_METHODOLOGY, (
                "El rendimiento reportado es un dato de detalle de la fuente y no sustituye "
                "el rendimiento agregado calculado como razón de sumas."
            )],
        )

    def summary(
        self,
        filters: AgricultureFilters,
    ) -> AnalyticalResponse[SummaryData | None]:
        version = self.repository.latest_published_version()
        result = self.repository.summary(filters)
        data = self._summary_data(result) if result.record_count else None
        return AnalyticalResponse(
            data=data,
            meta=self._meta(version, filters),
            coverage=self._coverage(result),
            warnings=self._warnings(filters, result.coverage_status, version),
            methodology=_METHODOLOGY,
        )

    def series(
        self,
        filters: AgricultureFilters,
    ) -> AnalyticalResponse[list[SeriesPointOut]]:
        version = self.repository.latest_published_version()
        summary = self.repository.summary(filters)
        data = [
            SeriesPointOut.model_validate(point, from_attributes=True)
            for point in self.repository.series(filters)
        ]
        return AnalyticalResponse(
            data=data,
            meta=self._meta(version, filters),
            coverage=self._coverage(summary),
            warnings=self._warnings(filters, summary.coverage_status, version),
            methodology=_METHODOLOGY,
        )

    def rankings(
        self,
        filters: AgricultureFilters,
        *,
        dimension: str,
        limit: int,
    ) -> AnalyticalResponse[list[RankingItemOut]]:
        version = self.repository.latest_published_version()
        summary = self.repository.summary(filters)
        data = [
            RankingItemOut.model_validate(item, from_attributes=True)
            for item in self.repository.rankings(
                filters,
                dimension=dimension,
                indicator=filters.indicator,
                limit=limit,
            )
        ]
        return AnalyticalResponse(
            data=data,
            meta=self._meta(version, filters),
            coverage=self._coverage(summary),
            warnings=self._warnings(filters, summary.coverage_status, version),
            methodology=_METHODOLOGY,
        )

    @staticmethod
    def _summary_data(result: SummaryResult) -> SummaryData:
        assert result.planted_area_ha is not None
        assert result.harvested_area_ha is not None
        assert result.production_t is not None
        return SummaryData(
            planted_area_ha=result.planted_area_ha,
            harvested_area_ha=result.harvested_area_ha,
            production_t=result.production_t,
            yield_t_ha=result.yield_t_ha,
            record_count=result.record_count,
        )

    @staticmethod
    def _meta(version, filters: AgricultureFilters) -> ResponseMeta:
        return ResponseMeta(
            source_version=version.version_label if version is not None else None,
            source_version_id=version.id if version is not None else None,
            indicator=filters.indicator.value,
            period_mode=filters.period_mode.value,
            unit=indicator_unit(filters.indicator),
            filters=filters.model_dump(mode="json", by_alias=True, exclude_none=True),
        )

    @staticmethod
    def _coverage(result: SummaryResult) -> CoverageEnvelope:
        return CoverageEnvelope(
            status=result.coverage_status,
            year_from=result.year_from,
            year_to=result.year_to,
            record_count=result.record_count,
        )

    @staticmethod
    def _warnings(filters, coverage_status: str, version) -> list[AnalyticalWarningOut]:
        warnings: list[AnalyticalWarning] = []
        if version is not None:
            warnings.extend(
                comparison_warnings(filters, latest_year=version.coverage_end_year)
            )
        if coverage_status == "PARTIAL":
            warnings.append(
                AnalyticalWarning(
                    code="PARTIAL_SEMESTER_COVERAGE",
                    message="Solo está disponible uno de los dos semestres del año agrícola.",
                )
            )
        return [
            AnalyticalWarningOut(code=warning.code, message=warning.message)
            for warning in warnings
        ]
