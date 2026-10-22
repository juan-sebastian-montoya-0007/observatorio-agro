def test_openapi_lists_read_only_catalog_and_geography_routes(client):
    document = client.get("/openapi.json").json()
    expected_paths = {
        "/api/v1/catalog/crops",
        "/api/v1/catalog/periods",
        "/api/v1/catalog/sources",
        "/api/v1/geography/departments",
        "/api/v1/geography/municipalities",
    }

    assert expected_paths <= set(document["paths"])
    for path in expected_paths:
        assert set(document["paths"][path]) == {"get"}
    assert not any("import" in path for path in document["paths"])
