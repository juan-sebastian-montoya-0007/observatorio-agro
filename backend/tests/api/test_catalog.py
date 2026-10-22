def test_crops_keep_base_code_and_nested_variants(client, imported_dataset):
    response = client.get("/api/v1/catalog/crops")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta", "coverage", "warnings", "methodology"}
    assert body["data"] == [
        {
            "id": body["data"][0]["id"],
            "base_code": "10807",
            "name": "PAPA",
            "cycle": "TRANSITORIO",
            "group": "ALIMENTARIOS",
            "subgroup": "TUBÉRCULOS",
            "general_classification": "ALIMENTARIOS",
            "variants": [
                {
                    "id": body["data"][0]["variants"][0]["id"],
                    "source_code": "1080702",
                    "disaggregation": "PAPA CAPIRA",
                    "scientific_name": "Solanum tuberosum",
                },
                {
                    "id": body["data"][0]["variants"][1]["id"],
                    "source_code": "1080701",
                    "disaggregation": "PAPA CRIOLLA",
                    "scientific_name": "Solanum tuberosum",
                },
            ],
        }
    ]


def test_periods_and_sources_expose_provenance_without_local_paths(client, imported_dataset):
    periods = client.get("/api/v1/catalog/periods").json()["data"]
    sources = client.get("/api/v1/catalog/sources").json()["data"]

    assert periods == [
        {
            "year": 2025,
            "period_type": "SEMESTER_A",
            "label": "2025A",
            "chronological_order": 20251,
        }
    ]
    assert len(sources) == 1
    assert len(sources[0]["sha256"]) == 64
    assert sources[0]["coverage"] == {"year_from": 2025, "year_to": 2025}
    assert sources[0]["status"] == "PUBLISHED"
    assert "path" not in sources[0]
    assert "file_path" not in sources[0]
