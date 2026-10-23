from decimal import Decimal

import pytest

from app.models import Period, PeriodType, SourceVersion
from app.repositories.agriculture import AgricultureRepository
from app.schemas.filters import AgricultureFilters
from app.statistics import Indicator, PeriodMode


@pytest.fixture
def repository(session):
    return AgricultureRepository(session)


@pytest.fixture
def seeded_records(session, fact_factory):
    session.add_all(
        [
            fact_factory(
                crop_variant_id=1,
                harvested_area_ha=Decimal("2"),
                production_t=Decimal("12"),
                source_row=10,
            ),
            fact_factory(
                crop_variant_id=2,
                harvested_area_ha=Decimal("3"),
                production_t=Decimal("18"),
                source_row=11,
            ),
        ]
    )
    session.commit()


def test_summary_uses_ratio_of_sums(repository, seeded_records):
    result = repository.summary(AgricultureFilters(year_from=2024, year_to=2024))

    assert result.production_t == Decimal("30")
    assert result.harvested_area_ha == Decimal("5")
    assert result.yield_t_ha == Decimal("6")


def test_summary_applies_every_supported_dimension_filter(repository, seeded_records):
    result = repository.summary(
        AgricultureFilters(
            department_code="05",
            municipality_code="05001",
            crop_id=1,
            crop_variant_id=1,
            group="ALIMENTARIOS",
            subgroup="TUBÉRCULOS",
            cycle="TRANSITORIO",
            physical_state="EN FRESCO",
            year_from=2024,
            year_to=2024,
        )
    )

    assert result.production_t == Decimal("12")
    assert result.record_count == 1


def test_empty_combination_returns_unavailable_metrics_not_zero(repository, seeded_records):
    result = repository.summary(
        AgricultureFilters(
            department_code="08",
            year_from=2024,
            year_to=2024,
        )
    )

    assert result.record_count == 0
    assert result.production_t is None
    assert result.harvested_area_ha is None
    assert result.yield_t_ha is None
    assert result.coverage_status == "EMPTY"


def test_zero_harvested_area_returns_unavailable_yield(session, fact_factory, repository):
    session.add(
        fact_factory(
            harvested_area_ha=Decimal("0"),
            production_t=Decimal("5"),
        )
    )
    session.commit()

    result = repository.summary(AgricultureFilters(year_from=2024, year_to=2024))

    assert result.production_t == Decimal("5")
    assert result.yield_t_ha is None


def test_queries_ignore_newer_staged_source_versions(
    session,
    fact_factory,
    repository,
    seeded_records,
):
    session.add(
        SourceVersion(
            id=2,
            source_id=1,
            version_label="staged",
            coverage_start_year=2019,
            coverage_end_year=2025,
            sha256="b" * 64,
            file_name="staged.xlsx",
            status="STAGED",
        )
    )
    session.flush()
    session.add(
        fact_factory(
            source_version_id=2,
            production_t=Decimal("999"),
            source_row=99,
        )
    )
    session.commit()

    result = repository.summary(AgricultureFilters(year_from=2024, year_to=2024))

    assert result.production_t == Decimal("30")


def test_agricultural_year_excludes_overlapping_annual_transient_fact(
    session,
    fact_factory,
    repository,
):
    semester_a = Period(
        id=2,
        year=2024,
        period_type=PeriodType.SEMESTER_A,
        original_label="2024A",
        chronological_order=20241,
    )
    semester_b = Period(
        id=3,
        year=2024,
        period_type=PeriodType.SEMESTER_B,
        original_label="2024B",
        chronological_order=20242,
    )
    session.add_all([semester_a, semester_b])
    session.flush()
    session.add_all(
        [
            fact_factory(
                period_id=1,
                production_t=Decimal("100"),
                harvested_area_ha=Decimal("50"),
                source_row=10,
            ),
            fact_factory(
                period_id=2,
                production_t=Decimal("40"),
                harvested_area_ha=Decimal("20"),
                source_row=11,
            ),
        ]
    )
    session.add(
        fact_factory(
            period_id=3,
            production_t=Decimal("60"),
            harvested_area_ha=Decimal("30"),
            source_row=12,
        )
    )
    session.commit()

    result = repository.summary(
        AgricultureFilters(
            year_from=2024,
            year_to=2024,
            period_mode=PeriodMode.AGRICULTURAL_YEAR,
        )
    )

    assert result.production_t == Decimal("100")
    assert result.harvested_area_ha == Decimal("50")
    assert result.coverage_status == "AVAILABLE"


@pytest.mark.parametrize("limit", [0, 101])
def test_rankings_enforce_bounded_limit(repository, seeded_records, limit):
    with pytest.raises(ValueError, match="1 and 100"):
        repository.rankings(
            AgricultureFilters(year_from=2024, year_to=2024),
            dimension="crop",
            indicator=Indicator.PRODUCTION,
            limit=limit,
        )


@pytest.mark.parametrize(
    ("period_type", "production"),
    [("ANNUAL", "100"), ("SEMESTER_A", "40"), ("SEMESTER_B", "60")],
)
def test_source_queries_aggregate_only_the_selected_period(
    session, fact_factory, repository, period_type, production
):
    session.add_all(
        [
            Period(
                id=2, year=2024, period_type=PeriodType.SEMESTER_A,
                original_label="2024A", chronological_order=20241,
            ),
            Period(
                id=3, year=2024, period_type=PeriodType.SEMESTER_B,
                original_label="2024B", chronological_order=20242,
            ),
        ]
    )
    session.flush()
    session.add_all(
        [
            fact_factory(period_id=1, production_t=Decimal("100"), source_row=10),
            fact_factory(period_id=2, production_t=Decimal("40"), source_row=11),
            fact_factory(period_id=3, production_t=Decimal("60"), source_row=12),
        ]
    )
    session.commit()
    filters = AgricultureFilters.model_validate(
        {
            "year_from": 2024,
            "year_to": 2024,
            "period_mode": "SOURCE",
            "period_type": period_type,
        }
    )

    summary = repository.summary(filters)
    series = repository.series(filters)
    rankings = repository.rankings(filters, "crop", Indicator.PRODUCTION, 10)

    assert summary.production_t == Decimal(production)
    assert summary.record_count == 1
    assert summary.coverage_status == "AVAILABLE"
    assert len(series) == 1
    assert series[0].period_type == period_type
    assert series[0].production_t == Decimal(production)
    assert len(rankings) == 1
    assert rankings[0].value == Decimal(production)
    assert rankings[0].record_count == 1
