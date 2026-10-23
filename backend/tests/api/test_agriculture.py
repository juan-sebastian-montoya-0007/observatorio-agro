import pytest


def test_summary_exposes_source_coverage_warnings_and_methodology(client, imported_dataset):
    body = client.get(
        "/api/v1/agriculture/summary",
        params={"year_from": 2021, "year_to": 2022},
    ).json()

    assert set(body) == {"data", "meta", "coverage", "warnings", "methodology"}
    assert body["meta"]["source_version"]
    assert body["coverage"]["status"] == "EMPTY"
    assert {warning["code"] for warning in body["warnings"]} == {
        "TRANSIENT_METHODOLOGY_BREAK_2021_2022"
    }
    assert body["methodology"]


def test_summary_marks_single_semester_as_partial(client, imported_dataset):
    body = client.get(
        "/api/v1/agriculture/summary",
        params={"period_mode": "AGRICULTURAL_YEAR"},
    ).json()

    assert body["coverage"]["status"] == "PARTIAL"
    assert "PARTIAL_SEMESTER_COVERAGE" in {
        warning["code"] for warning in body["warnings"]
    }
    assert body["data"]["production_t"] == "54.0000"
    assert body["data"]["yield_t_ha"] == "2.0000"


def test_series_and_crop_rankings_return_real_values(client, imported_dataset):
    series = client.get("/api/v1/agriculture/series").json()["data"]
    rankings = client.get(
        "/api/v1/agriculture/rankings",
        params={"dimension": "crop", "indicator": "production_t", "limit": 10},
    ).json()["data"]

    assert series[0]["production_t"] == "54.0000"
    assert rankings[0]["name"] == "PAPA"
    assert rankings[0]["value"] == "54.0000"


def test_municipal_ranking_requires_department_parent(client, imported_dataset):
    response = client.get(
        "/api/v1/agriculture/rankings",
        params={"dimension": "municipality"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MISSING_PARENT_FILTER"


@pytest.mark.parametrize("endpoint", ["summary", "series", "rankings"])
@pytest.mark.parametrize(
    "params",
    [
        {"period_mode": "SOURCE"},
        {"period_mode": "AGRICULTURAL_YEAR", "period_type": "SEMESTER_A"},
        {"period_mode": "SOURCE", "period_type": "OTHER"},
    ],
)
def test_analytics_reject_invalid_source_period_combinations(client, endpoint, params):
    response = client.get(
        f"/api/v1/agriculture/{endpoint}",
        params={**params, "dimension": "crop"} if endpoint == "rankings" else params,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("endpoint", ["summary", "series", "rankings"])
@pytest.mark.parametrize(
    ("indicator", "unit"),
    [
        ("planted_area_ha", "ha"),
        ("harvested_area_ha", "ha"),
        ("production_t", "t"),
        ("yield_t_ha", "t/ha"),
    ],
)
def test_analytics_metadata_exposes_exact_units_and_applied_filters(
    client, imported_dataset, endpoint, indicator, unit
):
    params = {
        "department": "05",
        "municipality": "05001",
        "crop": 1,
        "crop_variant": 1,
        "group": "ALIMENTARIOS",
        "subgroup": "TUBÉRCULOS",
        "cycle": "TRANSITORIO",
        "physical_state": "EN FRESCO",
        "year_from": 2025,
        "year_to": 2025,
        "indicator": indicator,
        "period_mode": "SOURCE",
        "period_type": "SEMESTER_A",
    }
    response = client.get(
        f"/api/v1/agriculture/{endpoint}",
        params={**params, "dimension": "crop"} if endpoint == "rankings" else params,
    )

    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["unit"] == unit
    assert meta["filters"] == params


def test_default_analytics_metadata_uses_agricultural_year(client, imported_dataset):
    body = client.get("/api/v1/agriculture/summary").json()

    assert body["meta"]["period_mode"] == "AGRICULTURAL_YEAR"
    assert body["meta"]["filters"] == {
        "year_from": 2019,
        "year_to": 2025,
        "period_mode": "AGRICULTURAL_YEAR",
        "indicator": "production_t",
    }
