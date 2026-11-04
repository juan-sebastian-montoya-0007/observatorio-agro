from datetime import datetime


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


def test_periods_and_sources_expose_complete_provenance_without_local_paths(
    client,
    imported_dataset,
):
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
    source = sources[0]
    latest_import = source.pop("latest_import")
    sha256 = source.pop("sha256")

    assert source == {
        "id": imported_dataset.source_version_id,
        "name": "Evaluaciones Agropecuarias Municipales (EVA)",
        "publisher": "UPRA",
        "description": (
            "Evaluaciones Agropecuarias Municipales (EVA), publicadas por la UPRA."
        ),
        "official_url": "https://upra.gov.co/es-co/eva/eva-2025",
        "reuse_terms": None,
        "version_label": "2025-2025",
        "available_date": None,
        "notes": (
            "Fuente: EVA -UPRA, con base en información municipal\n"
            "* Las cifras de los dos últimos años son susceptibles de modificación."
        ),
        "coverage": {"year_from": 2025, "year_to": 2025},
        "variables": [
            "planted_area_ha",
            "harvested_area_ha",
            "production_t",
            "reported_yield_t_ha",
        ],
        "record_count": 2,
        "status": "PUBLISHED",
    }
    assert len(sha256) == 64
    assert latest_import == {
        "id": imported_dataset.import_run_id,
        "started_at": latest_import["started_at"],
        "finished_at": latest_import["finished_at"],
        "status": "SUCCEEDED",
        "rows_read": 2,
        "rows_inserted": 2,
        "rows_rejected": 0,
        "summary": {"warning_count": 0},
        "importer_version": "1.0.0",
    }
    assert datetime.fromisoformat(latest_import["started_at"])
    assert datetime.fromisoformat(latest_import["finished_at"])
    assert "path" not in source
    assert "file_path" not in source
