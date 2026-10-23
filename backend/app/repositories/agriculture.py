from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Numeric, Select, and_, cast, exists, func, literal, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    AgriculturalRecord,
    Crop,
    CropGroup,
    CropSubgroup,
    CropVariant,
    Department,
    Municipality,
    Period,
    PeriodType,
    PhysicalState,
    SourceVersion,
)
from app.schemas.agriculture import AgriculturalRecordOut
from app.schemas.filters import AgricultureFilters
from app.schemas.records import (
    RecordPageQuery,
    RecordSelectionQuery,
    RecordSortField,
    SortDirection,
)
from app.statistics import Indicator, PeriodMode


@dataclass(frozen=True, slots=True)
class SummaryResult:
    planted_area_ha: Decimal | None
    harvested_area_ha: Decimal | None
    production_t: Decimal | None
    yield_t_ha: Decimal | None
    record_count: int
    coverage_status: str
    year_from: int | None
    year_to: int | None


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    year: int
    period_type: str
    planted_area_ha: Decimal
    harvested_area_ha: Decimal
    production_t: Decimal
    yield_t_ha: Decimal | None
    record_count: int


@dataclass(frozen=True, slots=True)
class RankingItem:
    rank: int
    id: str | int
    name: str
    value: Decimal
    record_count: int


@dataclass(frozen=True, slots=True)
class RecordPage:
    items: list[AgriculturalRecordOut]
    total: int
    page: int
    page_size: int


class AgricultureRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def latest_published_version(self) -> SourceVersion | None:
        return self.session.scalar(
            select(SourceVersion)
            .where(SourceVersion.status == "PUBLISHED")
            .order_by(SourceVersion.coverage_end_year.desc(), SourceVersion.id.desc())
            .limit(1)
        )

    def records(self, query: RecordPageQuery) -> RecordPage:
        version = self.latest_published_version()
        if version is None:
            return RecordPage([], 0, query.page, query.page_size)

        total = self._count_records(version.id, query)
        statement = (
            self._record_statement(version.id, query)
            .limit(query.page_size)
            .offset((query.page - 1) * query.page_size)
        )
        items = [
            AgriculturalRecordOut.model_validate(row, from_attributes=True)
            for row in self.session.execute(statement)
        ]
        return RecordPage(items, total, query.page, query.page_size)

    def count_records(
        self,
        selection: RecordSelectionQuery,
        source_version_id: int | None,
    ) -> int:
        if source_version_id is None:
            return 0
        return self._count_records(source_version_id, selection)

    def iter_records(
        self,
        selection: RecordSelectionQuery,
        batch_size: int,
        source_version_id: int | None,
    ) -> Iterator[AgriculturalRecordOut]:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if source_version_id is None:
            return

        statement = self._record_statement(source_version_id, selection).execution_options(
            stream_results=True,
            yield_per=batch_size,
        )
        result = self.session.execute(statement)
        try:
            for partition in result.partitions(batch_size):
                for row in partition:
                    yield AgriculturalRecordOut.model_validate(row, from_attributes=True)
        finally:
            result.close()

    def _count_records(
        self,
        source_version_id: int,
        selection: RecordSelectionQuery,
    ) -> int:
        total = self.session.scalar(
            self._with_joins(select(func.count(AgriculturalRecord.id))).where(
                *self._conditions(source_version_id, selection)
            )
        )
        return int(total or 0)

    @staticmethod
    def _record_ordering(selection: RecordSelectionQuery):
        sort_column = {
            RecordSortField.YEAR: Period.year,
            RecordSortField.PERIOD_TYPE: Period.period_type,
            RecordSortField.DEPARTMENT: Department.name,
            RecordSortField.MUNICIPALITY: Municipality.name,
            RecordSortField.CROP: Crop.name,
            RecordSortField.CROP_VARIANT: CropVariant.disaggregation,
            RecordSortField.PHYSICAL_STATE: PhysicalState.name,
            RecordSortField.PLANTED_AREA: AgriculturalRecord.planted_area_ha,
            RecordSortField.HARVESTED_AREA: AgriculturalRecord.harvested_area_ha,
            RecordSortField.PRODUCTION: AgriculturalRecord.production_t,
            RecordSortField.REPORTED_YIELD: AgriculturalRecord.reported_yield_t_ha,
            RecordSortField.SOURCE_ROW: AgriculturalRecord.source_row,
        }[selection.sort_by]
        ordering = (
            sort_column.asc()
            if selection.sort_direction is SortDirection.ASC
            else sort_column.desc()
        )
        return ordering.nullslast(), AgriculturalRecord.id.asc()

    def _record_statement(
        self,
        source_version_id: int,
        selection: RecordSelectionQuery,
    ) -> Select:
        return (
            self._with_joins(
                select(
                AgriculturalRecord.id,
                Department.code.label("department_code"),
                Department.name.label("department_name"),
                Municipality.code.label("municipality_code"),
                Municipality.name.label("municipality_name"),
                Period.year, Period.period_type,
                Crop.id.label("crop_id"),
                Crop.base_code.label("crop_base_code"),
                Crop.name.label("crop_name"),
                CropVariant.id.label("crop_variant_id"),
                CropVariant.source_code.label("crop_variant_source_code"),
                CropVariant.disaggregation.label("crop_variant_disaggregation"),
                PhysicalState.name.label("physical_state"),
                AgriculturalRecord.planted_area_ha,
                AgriculturalRecord.harvested_area_ha,
                AgriculturalRecord.production_t,
                AgriculturalRecord.reported_yield_t_ha,
                AgriculturalRecord.source_version_id,
                SourceVersion.version_label.label("source_version_label"),
                AgriculturalRecord.trace_metadata["sheet"].as_string().label("source_sheet"),
                AgriculturalRecord.source_row,
                )
            )
            .join(SourceVersion, SourceVersion.id == AgriculturalRecord.source_version_id)
            .where(*self._conditions(source_version_id, selection))
            .order_by(*self._record_ordering(selection))
        )

    def summary(self, filters: AgricultureFilters) -> SummaryResult:
        version = self.latest_published_version()
        if version is None:
            return self._empty_summary()

        planted = func.sum(AgriculturalRecord.planted_area_ha)
        harvested = func.sum(AgriculturalRecord.harvested_area_ha)
        production = func.sum(AgriculturalRecord.production_t)
        yield_value = cast(
            production / func.nullif(harvested, 0), Numeric(18, 4)
        )
        statement = self._with_joins(
            select(
                func.count(AgriculturalRecord.id).label("record_count"),
                planted.label("planted_area_ha"),
                harvested.label("harvested_area_ha"),
                production.label("production_t"),
                yield_value.label("yield_t_ha"),
                func.min(Period.year).label("year_from"),
                func.max(Period.year).label("year_to"),
            )
        ).where(*self._conditions(version.id, filters))
        row = self.session.execute(statement).one()
        record_count = int(row.record_count)
        if record_count == 0:
            return self._empty_summary()

        return SummaryResult(
            planted_area_ha=row.planted_area_ha,
            harvested_area_ha=row.harvested_area_ha,
            production_t=row.production_t,
            yield_t_ha=row.yield_t_ha,
            record_count=record_count,
            coverage_status=self._coverage_status(version.id, filters),
            year_from=row.year_from,
            year_to=row.year_to,
        )

    def series(self, filters: AgricultureFilters) -> list[SeriesPoint]:
        version = self.latest_published_version()
        if version is None:
            return []

        planted = func.sum(AgriculturalRecord.planted_area_ha)
        harvested = func.sum(AgriculturalRecord.harvested_area_ha)
        production = func.sum(AgriculturalRecord.production_t)
        yield_value = cast(
            production / func.nullif(harvested, 0), Numeric(18, 4)
        )
        period_expression = (
            Period.period_type
            if filters.period_mode is PeriodMode.SOURCE
            else literal("AGRICULTURAL_YEAR")
        )
        grouping = [Period.year]
        ordering = [Period.year]
        if filters.period_mode is PeriodMode.SOURCE:
            grouping.append(Period.period_type)
            ordering.append(Period.period_type)

        statement = (
            self._with_joins(
                select(
                    Period.year.label("year"),
                    period_expression.label("period_type"),
                    planted.label("planted_area_ha"),
                    harvested.label("harvested_area_ha"),
                    production.label("production_t"),
                    yield_value.label("yield_t_ha"),
                    func.count(AgriculturalRecord.id).label("record_count"),
                )
            )
            .where(*self._conditions(version.id, filters))
            .group_by(*grouping)
            .order_by(*ordering)
        )
        rows = self.session.execute(statement).all()
        return [
            SeriesPoint(
                year=row.year,
                period_type=(
                    row.period_type.value
                    if isinstance(row.period_type, PeriodType)
                    else str(row.period_type)
                ),
                planted_area_ha=row.planted_area_ha,
                harvested_area_ha=row.harvested_area_ha,
                production_t=row.production_t,
                yield_t_ha=row.yield_t_ha,
                record_count=int(row.record_count),
            )
            for row in rows
        ]

    def rankings(
        self,
        filters: AgricultureFilters,
        dimension: str,
        indicator: Indicator,
        limit: int,
    ) -> list[RankingItem]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        dimensions = {
            "department": (Department.code, Department.name),
            "municipality": (Municipality.code, Municipality.name),
            "crop": (Crop.id, Crop.name),
        }
        if dimension not in dimensions:
            raise ValueError("dimension must be department, municipality, or crop")

        version = self.latest_published_version()
        if version is None:
            return []

        dimension_id, dimension_name = dimensions[dimension]
        planted = func.sum(AgriculturalRecord.planted_area_ha)
        harvested = func.sum(AgriculturalRecord.harvested_area_ha)
        production = func.sum(AgriculturalRecord.production_t)
        metric = {
            Indicator.PLANTED_AREA: planted,
            Indicator.HARVESTED_AREA: harvested,
            Indicator.PRODUCTION: production,
            Indicator.YIELD: cast(
                production / func.nullif(harvested, 0), Numeric(18, 4)
            ),
        }[indicator]
        statement = (
            self._with_joins(
                select(
                    dimension_id.label("dimension_id"),
                    dimension_name.label("name"),
                    metric.label("value"),
                    func.count(AgriculturalRecord.id).label("record_count"),
                )
            )
            .where(*self._conditions(version.id, filters))
            .group_by(dimension_id, dimension_name)
            .having(metric.is_not(None))
            .order_by(metric.desc().nullslast(), func.lower(dimension_name))
            .limit(limit)
        )
        rows = self.session.execute(statement).all()
        return [
            RankingItem(
                rank=index,
                id=row.dimension_id,
                name=row.name,
                value=row.value,
                record_count=int(row.record_count),
            )
            for index, row in enumerate(rows, start=1)
        ]

    @staticmethod
    def _with_joins(statement: Select) -> Select:
        return (
            statement.select_from(AgriculturalRecord)
            .join(Municipality, Municipality.id == AgriculturalRecord.municipality_id)
            .join(Department, Department.code == Municipality.department_code)
            .join(CropVariant, CropVariant.id == AgriculturalRecord.crop_variant_id)
            .join(Crop, Crop.id == CropVariant.crop_id)
            .join(CropGroup, CropGroup.id == Crop.group_id)
            .join(CropSubgroup, CropSubgroup.id == Crop.subgroup_id)
            .join(PhysicalState, PhysicalState.id == AgriculturalRecord.physical_state_id)
            .join(Period, Period.id == AgriculturalRecord.period_id)
        )

    def _conditions(
        self,
        source_version_id: int,
        filters: AgricultureFilters,
    ) -> list[object]:
        conditions: list[object] = [
            AgriculturalRecord.source_version_id == source_version_id,
            Period.year >= filters.year_from,
            Period.year <= filters.year_to,
        ]
        optional_conditions = (
            (filters.department_code, Department.code),
            (filters.municipality_code, Municipality.code),
            (filters.crop_id, Crop.id),
            (filters.crop_variant_id, CropVariant.id),
            (filters.group, CropGroup.name),
            (filters.subgroup, CropSubgroup.name),
            (filters.cycle, Crop.cycle),
            (filters.physical_state, PhysicalState.name),
        )
        for value, column in optional_conditions:
            if value is not None:
                conditions.append(column == value)
        if isinstance(filters, RecordSelectionQuery) and filters.search:
            conditions.append(or_(
                *(column.icontains(filters.search, autoescape=True) for column in (
                    Department.name, Municipality.name, Crop.name, CropVariant.disaggregation,
                ))
            ))
        if filters.period_mode is PeriodMode.AGRICULTURAL_YEAR:
            conditions.append(self._agricultural_year_condition())
        else:
            conditions.append(Period.period_type == filters.period_type)
        return conditions

    @staticmethod
    def _agricultural_year_condition():
        other_fact = aliased(AgriculturalRecord)
        other_period = aliased(Period)
        has_semester = exists(
            select(1)
            .select_from(other_fact)
            .join(other_period, other_period.id == other_fact.period_id)
            .where(
                other_fact.source_version_id == AgriculturalRecord.source_version_id,
                other_fact.municipality_id == AgriculturalRecord.municipality_id,
                other_fact.crop_variant_id == AgriculturalRecord.crop_variant_id,
                other_fact.physical_state_id == AgriculturalRecord.physical_state_id,
                other_period.year == Period.year,
                other_period.period_type.in_(
                    [PeriodType.SEMESTER_A, PeriodType.SEMESTER_B]
                ),
            )
        )
        transient = func.lower(Crop.cycle).contains("trans")
        return or_(
            and_(~transient, Period.period_type == PeriodType.ANNUAL),
            and_(
                transient,
                or_(
                    Period.period_type.in_(
                        [PeriodType.SEMESTER_A, PeriodType.SEMESTER_B]
                    ),
                    and_(Period.period_type == PeriodType.ANNUAL, ~has_semester),
                ),
            ),
        )

    def _coverage_status(
        self,
        source_version_id: int,
        filters: AgricultureFilters,
    ) -> str:
        if filters.period_mode is PeriodMode.SOURCE:
            return "AVAILABLE"

        statement = (
            self._with_joins(select(Crop.cycle, Period.year, Period.period_type))
            .where(*self._conditions(source_version_id, filters))
            .distinct()
        )
        rows = self.session.execute(statement).all()
        if not rows:
            return "EMPTY"

        semester_types = {PeriodType.SEMESTER_A, PeriodType.SEMESTER_B}
        transient_periods: dict[int, set[PeriodType]] = {}
        for cycle, year, period_type in rows:
            if "trans" in cycle.casefold() and period_type in semester_types:
                transient_periods.setdefault(year, set()).add(period_type)
        if any(types != semester_types for types in transient_periods.values()):
            return "PARTIAL"
        return "AVAILABLE"

    @staticmethod
    def _empty_summary() -> SummaryResult:
        return SummaryResult(
            planted_area_ha=None,
            harvested_area_ha=None,
            production_t=None,
            yield_t_ha=None,
            record_count=0,
            coverage_status="EMPTY",
            year_from=None,
            year_to=None,
        )
