from decimal import Decimal

import pytest
from sqlalchemy import event

from app.models import (
    Crop,
    CropGroup,
    CropSubgroup,
    CropVariant,
    Department,
    Municipality,
    Period,
    PeriodType,
    SourceVersion,
)
from app.repositories.agriculture import AgricultureRepository
from app.schemas.records import RecordPageQuery, RecordSelectionQuery


@pytest.fixture
def records_repository(session, fact_factory):
    group = CropGroup(id=2, name="CEREALES")
    subgroup = CropSubgroup(id=2, name="GRANOS", group=group)
    crop = Crop(
        id=2, base_code="101", name="ARROZ", cycle="PERMANENTE",
        group=group, subgroup=subgroup, general_classification="ALIMENTARIOS",
    )
    session.add_all([
        Municipality(id=2, code="05002", name="ABEJORRAL", department_code="05"),
        Municipality(
            id=3, code="08001", name="BARRANQUILLA",
            department=Department(code="08", name="ATLÁNTICO"),
        ),
        CropVariant(id=3, crop_id=1, source_code="1080703", disaggregation="PAPA ROJA"),
        CropVariant(id=4, crop=crop, source_code="10101", disaggregation="ARROZ BLANCO"),
    ])
    session.flush()
    session.add_all([
        fact_factory(id=40, crop_variant_id=1, production_t=Decimal("18")),
        fact_factory(id=10, crop_variant_id=2, production_t=Decimal("9"), source_row=11),
        fact_factory(
            id=30, municipality_id=2, crop_variant_id=3,
            production_t=Decimal("18"), source_row=12,
        ),
        fact_factory(
            id=20, municipality_id=3, crop_variant_id=4,
            production_t=Decimal("3"), source_row=13,
        ),
    ])
    session.commit()
    return AgricultureRepository(session)


def test_records_page_counts_all_matches_and_preserves_detail(records_repository):
    result = records_repository.records(RecordPageQuery(page=2, page_size=2))

    assert (result.total, result.page, result.page_size) == (4, 2, 2)
    assert [item.id for item in result.items] == [30, 40]
    item = result.items[1]
    assert (item.department_code, item.department_name) == ("05", "ANTIOQUIA")
    assert (item.municipality_code, item.municipality_name) == ("05001", "MEDELLÍN")
    assert (item.year, item.period_type) == (2024, "ANNUAL")
    assert (item.crop_id, item.crop_base_code, item.crop_name) == (1, "10807", "PAPA")
    assert (item.crop_variant_id, item.crop_variant_source_code) == (1, "1080701")
    assert item.crop_variant_disaggregation == "PAPA CRIOLLA"
    assert item.physical_state == "EN FRESCO"
    assert item.planted_area_ha == Decimal("10.0000")
    assert item.harvested_area_ha == Decimal("9.0000")
    assert item.production_t == Decimal("18.0000")
    assert item.reported_yield_t_ha == Decimal("2.0000")
    assert (item.source_version_id, item.source_version_label) == (1, "2019-2025")
    assert (item.source_sheet, item.source_row) == ("BasePagina", 10)


@pytest.mark.parametrize(
    ("search", "ids"),
    [("aNtIoQuIa", [10, 30, 40]), ("mEdElLíN", [10, 40]),
     ("pApA", [10, 30, 40]), ("cRiOlLa", [40]), ("no existe", []),
     ("10807", []), ("%", []), ("_", [])],
)
def test_records_searches_only_names_case_insensitively(records_repository, search, ids):
    result = records_repository.records(RecordPageQuery(search=search, page_size=1))

    assert result.total == len(ids)
    assert [item.id for item in result.items] == ids[:1]


@pytest.mark.parametrize(
    "filters",
    [dict(department_code="08"), dict(department_code="05", municipality_code="05002"),
     dict(crop_id=2), dict(crop_variant_id=4), dict(group="CEREALES"),
     dict(subgroup="GRANOS"), dict(cycle="PERMANENTE"), dict(physical_state="SECO"),
     dict(year_from=2025), dict(year_to=2023)],
)
def test_records_apply_each_existing_filter(records_repository, filters):
    result = records_repository.records(RecordPageQuery(**filters))

    expected = (
        [] if any(key in filters for key in ("physical_state", "year_from", "year_to"))
        else [30] if "municipality_code" in filters else [20]
    )
    assert [item.id for item in result.items] == expected
    assert result.total == len(expected)


@pytest.mark.parametrize(
    ("direction", "ids"), [("asc", [20, 10, 30, 40]), ("desc", [30, 40, 10, 20])],
)
def test_records_sort_metrics_with_stable_id_tiebreak(records_repository, direction, ids):
    result = records_repository.records(
        RecordPageQuery(sort_by="production_t", sort_direction=direction)
    )

    assert [item.id for item in result.items] == ids


@pytest.mark.parametrize(
    ("sort_by", "ascending", "descending"),
    [
        ("year", [10, 20, 30, 40], [10, 20, 30, 40]),
        ("period_type", [10, 20, 30, 40], [10, 20, 30, 40]),
        ("department", [10, 30, 40, 20], [20, 10, 30, 40]),
        ("municipality", [30, 20, 10, 40], [10, 40, 20, 30]),
        ("crop", [20, 10, 30, 40], [10, 30, 40, 20]),
        ("crop_variant", [20, 10, 40, 30], [30, 40, 10, 20]),
        ("physical_state", [10, 20, 30, 40], [10, 20, 30, 40]),
        ("planted_area_ha", [10, 20, 30, 40], [10, 20, 30, 40]),
        ("harvested_area_ha", [10, 20, 30, 40], [10, 20, 30, 40]),
        ("production_t", [20, 10, 30, 40], [30, 40, 10, 20]),
        ("reported_yield_t_ha", [10, 20, 30, 40], [10, 20, 30, 40]),
        ("source_row", [40, 10, 30, 20], [20, 30, 10, 40]),
    ],
)
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_records_accept_every_allowlisted_sort(
    records_repository, sort_by, ascending, descending, direction
):
    result = records_repository.records(RecordPageQuery(sort_by=sort_by, sort_direction=direction))

    assert result.total == 4
    assert [item.id for item in result.items] == (ascending if direction == "asc" else descending)


def test_records_empty_page_keeps_total(records_repository):
    result = records_repository.records(RecordPageQuery(page=10, page_size=2))

    assert result.items == []
    assert result.total == 4


def test_records_selection_contract_has_no_pagination():
    selection = RecordSelectionQuery(search="PAPA", sort_by="crop", sort_direction="asc")

    assert selection.search == "PAPA"
    assert "page" not in RecordSelectionQuery.model_fields
    assert "page_size" not in RecordSelectionQuery.model_fields


def test_records_uses_database_limit_and_offset(session, records_repository):
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(session.bind, "before_cursor_execute", capture)
    try:
        records_repository.records(RecordPageQuery(page=2, page_size=1))
    finally:
        event.remove(session.bind, "before_cursor_execute", capture)

    detail = [sql for sql in statements if "source_row" in sql]
    assert len(detail) == 1
    assert "LIMIT" in detail[0] and "OFFSET" in detail[0]


def test_records_honors_temporal_selection_and_published_version(session, fact_factory):
    session.add_all([
        Period(
            id=2, year=2024, period_type=PeriodType.SEMESTER_A,
            original_label="2024A", chronological_order=20241,
        ),
        SourceVersion(
            id=2, source_id=1, version_label="staged", coverage_start_year=2019,
            coverage_end_year=2025, sha256="b" * 64, file_name="staged.xlsx", status="STAGED",
        ),
    ])
    session.flush()
    session.add_all([
        fact_factory(id=1), fact_factory(id=2, period_id=2, source_row=11),
        fact_factory(id=3, source_version_id=2, source_row=12),
    ])
    session.commit()
    repository = AgricultureRepository(session)

    agricultural_year = repository.records(RecordPageQuery())
    source = repository.records(RecordPageQuery(period_mode="SOURCE", period_type="ANNUAL"))

    assert [item.id for item in agricultural_year.items] == [2]
    assert [item.id for item in source.items] == [1]


def test_records_without_published_version_returns_empty_page(session):
    result = AgricultureRepository(session).records(RecordPageQuery(page=3, page_size=5))

    assert result.items == []
    assert (result.total, result.page, result.page_size) == (0, 3, 5)
