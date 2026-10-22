from collections.abc import Iterable
from decimal import Decimal

from app.models import PeriodType
from app.statistics.types import (
    AnalyticalWarning,
    Coverage,
    PeriodMode,
    PeriodObservation,
    PeriodSelection,
)


def weighted_yield(production: Decimal, harvested: Decimal) -> Decimal | None:
    if harvested == 0:
        return None
    return production / harvested


def select_period_grain(
    records: Iterable[PeriodObservation],
    mode: PeriodMode,
) -> PeriodSelection:
    candidates = tuple(records)
    if not candidates:
        return _selection((), (), Coverage("EMPTY", frozenset(), frozenset()), ())

    available = frozenset(record.period_type for record in candidates)
    if mode is PeriodMode.SOURCE:
        coverage = Coverage("COMPLETE", available, available)
        return _selection(candidates, (), coverage, ())

    is_transient = any("trans" in record.cycle.casefold() for record in candidates)
    if not is_transient:
        selected = tuple(
            record for record in candidates if record.period_type is PeriodType.ANNUAL
        )
        excluded = tuple(record for record in candidates if record not in selected)
        expected = frozenset({PeriodType.ANNUAL})
        status = "COMPLETE" if selected else "EMPTY"
        coverage = Coverage(status, frozenset(record.period_type for record in selected), expected)
        return _selection(selected, excluded, coverage, ())

    semester_types = frozenset({PeriodType.SEMESTER_A, PeriodType.SEMESTER_B})
    semesters = tuple(
        record for record in candidates if record.period_type in semester_types
    )
    if not semesters:
        annual = tuple(
            record for record in candidates if record.period_type is PeriodType.ANNUAL
        )
        excluded = tuple(record for record in candidates if record not in annual)
        expected = frozenset({PeriodType.ANNUAL})
        status = "COMPLETE" if annual else "EMPTY"
        coverage = Coverage(status, frozenset(record.period_type for record in annual), expected)
        return _selection(annual, excluded, coverage, ())

    used_types = frozenset(record.period_type for record in semesters)
    is_complete = semester_types <= used_types
    warnings: tuple[AnalyticalWarning, ...] = ()
    if not is_complete:
        warnings = (
            AnalyticalWarning(
                code="PARTIAL_SEMESTER_COVERAGE",
                message="Solo está disponible uno de los dos semestres del año agrícola.",
            ),
        )
    coverage = Coverage(
        "COMPLETE" if is_complete else "PARTIAL",
        used_types,
        semester_types,
    )
    excluded = tuple(record for record in candidates if record not in semesters)
    return _selection(semesters, excluded, coverage, warnings)


def _selection(
    selected: tuple[PeriodObservation, ...],
    excluded: tuple[PeriodObservation, ...],
    coverage: Coverage,
    warnings: tuple[AnalyticalWarning, ...],
) -> PeriodSelection:
    planted = sum((record.planted_area_ha for record in selected), start=Decimal("0"))
    harvested = sum((record.harvested_area_ha for record in selected), start=Decimal("0"))
    production = sum((record.production_t for record in selected), start=Decimal("0"))
    return PeriodSelection(
        planted_area_ha=planted,
        harvested_area_ha=harvested,
        production_t=production,
        yield_t_ha=weighted_yield(production, harvested),
        used_period_types=frozenset(record.period_type for record in selected),
        excluded_period_types=frozenset(record.period_type for record in excluded),
        coverage=coverage,
        warnings=warnings,
    )
