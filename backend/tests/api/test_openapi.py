def test_openapi_lists_read_only_catalog_and_geography_routes(client):
    document = client.get("/openapi.json").json()
    expected_paths = {
        "/api/v1/catalog/crops",
        "/api/v1/catalog/periods",
        "/api/v1/catalog/sources",
        "/api/v1/geography/departments",
        "/api/v1/geography/municipalities",
        "/api/v1/agriculture/records",
        "/api/v1/exports/agriculture",
    }

    assert expected_paths <= set(document["paths"])
    for path in expected_paths:
        assert set(document["paths"][path]) == {"get"}
    assert not any("import" in path for path in document["paths"])


def test_openapi_uses_observatorio_agro_title(client):
    document = client.get("/openapi.json").json()

    assert document["info"]["title"] == "Observatorio Agro API"


def test_openapi_records_exposes_selection_pagination_and_sort_enums(client):
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/api/v1/agriculture/records"]["get"]
    parameters = {parameter["name"]: parameter["schema"] for parameter in operation["parameters"]}

    assert {
        "search", "page", "page_size", "sort_by", "sort_direction", "period_type"
    } <= parameters.keys()
    assert parameters["page"]["minimum"] == 1
    assert parameters["page_size"]["maximum"] == 100
    schemas = document["components"]["schemas"]
    assert set(schemas["SortDirection"]["enum"]) == {"asc", "desc"}
    assert set(schemas["RecordSortField"]["enum"]) == {
        "year", "period_type", "department", "municipality", "crop", "crop_variant",
        "physical_state", "planted_area_ha", "harvested_area_ha", "production_t",
        "reported_yield_t_ha", "source_row",
    }


def test_openapi_export_exposes_format_and_shared_record_selection(client):
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/api/v1/exports/agriculture"]["get"]
    parameters = {parameter["name"]: parameter["schema"] for parameter in operation["parameters"]}

    assert {"format", "search", "sort_by", "sort_direction", "period_type"} <= parameters.keys()
    export_format = parameters["format"]["$ref"].rsplit("/", 1)[-1]
    assert set(document["components"]["schemas"][export_format]["enum"]) == {"csv", "xlsx"}
    assert "page" not in parameters
    assert "page_size" not in parameters
