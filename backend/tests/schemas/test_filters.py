import pytest
from pydantic import ValidationError

from app.schemas.filters import AgricultureFilters
from app.statistics import Indicator, PeriodMode, comparison_warnings


def test_filters_default_to_safe_agricultural_year():
    assert AgricultureFilters().period_mode is PeriodMode.AGRICULTURAL_YEAR


@pytest.mark.parametrize(
    "payload",
    [
        {"period_mode": "SOURCE"},
        {"period_mode": "SOURCE", "period_type": "OTHER"},
        {"period_mode": "AGRICULTURAL_YEAR", "period_type": "SEMESTER_A"},
    ],
)
def test_filters_reject_missing_or_incompatible_source_period(payload):
    with pytest.raises(ValidationError):
        AgricultureFilters.model_validate(payload)


@pytest.mark.parametrize("period_type", ["ANNUAL", "SEMESTER_A", "SEMESTER_B"])
def test_source_filters_accept_an_explicit_period(period_type):
    filters = AgricultureFilters.model_validate(
        {"period_mode": "SOURCE", "period_type": period_type}
    )

    assert filters.period_type.value == period_type


def test_filters_accept_aliases_and_valid_parent_relationship():
    filters = AgricultureFilters.model_validate(
        {
            "department": "05",
            "municipality": "05001",
            "year_from": 2019,
            "year_to": 2025,
            "period_mode": "AGRICULTURAL_YEAR",
        }
    )

    assert filters.department_code == "05"
    assert filters.municipality_code == "05001"
    assert filters.period_mode is PeriodMode.AGRICULTURAL_YEAR


@pytest.mark.parametrize(
    "payload",
    [
        {"year_from": 2018, "year_to": 2025},
        {"year_from": 2025, "year_to": 2024},
        {"municipality": "05001"},
        {"department": "08", "municipality": "05001"},
        {"department": "5", "municipality": "05001"},
    ],
)
def test_filters_reject_out_of_range_or_orphan_geography(payload):
    with pytest.raises(ValidationError):
        AgricultureFilters.model_validate(payload)


def test_comparison_warnings_cover_methodology_break_and_recent_years():
    filters = AgricultureFilters(
        year_from=2021,
        year_to=2025,
        cycle="TRANSITORIO",
        indicator=Indicator.PRODUCTION,
    )

    warnings = comparison_warnings(filters, latest_year=2025)

    assert {warning.code for warning in warnings} == {
        "TRANSIENT_METHODOLOGY_BREAK_2021_2022",
        "RECENT_DATA_PROVISIONAL",
    }


def test_planted_area_does_not_emit_harvest_methodology_break():
    filters = AgricultureFilters(
        year_from=2021,
        year_to=2022,
        cycle="TRANSITORIO",
        indicator=Indicator.PLANTED_AREA,
    )

    assert "TRANSIENT_METHODOLOGY_BREAK_2021_2022" not in {
        warning.code for warning in comparison_warnings(filters, latest_year=2025)
    }
