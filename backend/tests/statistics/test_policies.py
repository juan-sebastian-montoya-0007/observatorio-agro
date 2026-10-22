from decimal import Decimal

from app.models import PeriodType
from app.statistics import (
    PeriodMode,
    PeriodObservation,
    select_period_grain,
    weighted_yield,
)


def _record(
    period_type: PeriodType,
    production: str,
    harvested: str,
    *,
    cycle: str = "TRANSITORIO",
) -> PeriodObservation:
    return PeriodObservation(
        period_type=period_type,
        planted_area_ha=Decimal(harvested),
        harvested_area_ha=Decimal(harvested),
        production_t=Decimal(production),
        cycle=cycle,
    )


def test_weighted_yield_uses_ratio_of_sums_and_zero_is_unavailable():
    assert weighted_yield(Decimal("30"), Decimal("5")) == Decimal("6")
    assert weighted_yield(Decimal("0"), Decimal("0")) is None


def test_agricultural_year_prefers_semesters_for_transient_overlap():
    selected = select_period_grain(
        [
            _record(PeriodType.ANNUAL, "100", "50"),
            _record(PeriodType.SEMESTER_A, "40", "20"),
            _record(PeriodType.SEMESTER_B, "60", "30"),
        ],
        PeriodMode.AGRICULTURAL_YEAR,
    )

    assert selected.production_t == Decimal("100")
    assert selected.used_period_types == {
        PeriodType.SEMESTER_A,
        PeriodType.SEMESTER_B,
    }
    assert selected.excluded_period_types == {PeriodType.ANNUAL}
    assert selected.coverage.status == "COMPLETE"


def test_agricultural_year_marks_single_semester_as_partial():
    selected = select_period_grain(
        [_record(PeriodType.SEMESTER_A, "40", "20")],
        PeriodMode.AGRICULTURAL_YEAR,
    )

    assert selected.coverage.status == "PARTIAL"
    assert [warning.code for warning in selected.warnings] == [
        "PARTIAL_SEMESTER_COVERAGE"
    ]


def test_agricultural_year_uses_annual_for_permanent_crop():
    selected = select_period_grain(
        [
            _record(PeriodType.ANNUAL, "90", "30", cycle="PERMANENTE"),
            _record(PeriodType.SEMESTER_A, "40", "20", cycle="PERMANENTE"),
        ],
        PeriodMode.AGRICULTURAL_YEAR,
    )

    assert selected.production_t == Decimal("90")
    assert selected.used_period_types == {PeriodType.ANNUAL}
    assert selected.excluded_period_types == {PeriodType.SEMESTER_A}
