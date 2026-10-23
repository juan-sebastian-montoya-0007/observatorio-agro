from decimal import Decimal

import pytest


@pytest.fixture
def record_data(session, fact_factory):
    session.add_all([
        fact_factory(id=20, reported_yield_t_ha=Decimal("99.1250")),
        fact_factory(
            id=10, crop_variant_id=2, production_t=Decimal("36"),
            reported_yield_t_ha=None, trace_metadata={}, source_row=11,
        ),
    ])
    session.commit()


def test_records_envelope_preserves_numeric_detail_and_provenance(client, record_data):
    response = client.get("/api/v1/agriculture/records", params={"page_size": 1, "page": 2})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta", "coverage", "warnings", "methodology"}
    assert body["data"]["total"] == 2
    assert (body["data"]["page"], body["data"]["page_size"]) == (2, 1)
    item = body["data"]["items"][0]
    assert item["id"] == 20
    assert (item["department_code"], item["municipality_code"]) == ("05", "05001")
    assert item["reported_yield_t_ha"] == "99.1250"
    assert item["production_t"] == "18.0000"
    assert item["source_version_label"] == "2019-2025"
    assert (item["source_sheet"], item["source_row"]) == ("BasePagina", 10)
    assert "trace_metadata" not in item
    assert "yield_t_ha" not in item
    assert body["meta"]["filters"]["page_size"] == 1
    assert body["meta"]["filters"]["sort_by"] == "year"
    assert body["meta"]["filters"]["sort_direction"] == "desc"
    assert body["coverage"]["record_count"] == 2
    assert body["methodology"]


def test_records_search_metadata_and_coverage_match_all_results(client, record_data):
    response = client.get(
        "/api/v1/agriculture/records", params={"search": "cRiOlLa", "page": 2, "page_size": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {"items": [], "total": 1, "page": 2, "page_size": 1}
    assert body["coverage"]["record_count"] == 1
    assert body["meta"]["filters"]["search"] == "cRiOlLa"


def test_records_orders_and_serializes_nullable_detail(client, record_data):
    response = client.get(
        "/api/v1/agriculture/records", params={"sort_by": "production_t", "sort_direction": "desc"}
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["id"] for item in items] == [10, 20]
    assert items[0]["reported_yield_t_ha"] is None
    assert items[0]["source_sheet"] is None


@pytest.mark.parametrize("params", [
    {"sort_by": "production_t desc; drop table agricultural_records"},
    {"sort_direction": "DESC"}, {"page": 0}, {"page_size": 0}, {"page_size": 101},
    {"period_mode": "SOURCE"},
    {"period_mode": "AGRICULTURAL_YEAR", "period_type": "ANNUAL"},
    {"municipality": "05001"}, {"department": "08", "municipality": "05001"},
    {"year_from": 2025, "year_to": 2024}, {"period_mode": "SOURCE", "period_type": "OTHER"},
])
def test_records_rejects_invalid_selection_and_pagination(client, params):
    response = client.get("/api/v1/agriculture/records", params=params)

    assert response.status_code == 422


def test_records_empty_selection_preserves_envelope(client, record_data):
    response = client.get("/api/v1/agriculture/records", params={"search": "inexistente"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {"items": [], "total": 0, "page": 1, "page_size": 25}
    assert body["coverage"]["status"] == "EMPTY"
    assert body["coverage"]["record_count"] == 0


def test_records_without_source_returns_empty_envelope(client):
    response = client.get("/api/v1/agriculture/records")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] == 0
    assert body["data"]["items"] == []
    assert body["meta"]["source_version"] is None
    assert body["coverage"]["status"] == "EMPTY"
