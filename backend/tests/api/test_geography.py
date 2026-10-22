def test_municipalities_requires_and_applies_department(client, imported_dataset):
    response = client.get(
        "/api/v1/geography/municipalities",
        params={"department_code": "05"},
    )

    assert response.status_code == 200
    assert {item["department_code"] for item in response.json()["data"]} == {"05"}
    assert response.json()["data"][0]["code"] == "05001"


def test_departments_return_text_divipola_codes(client, imported_dataset):
    response = client.get("/api/v1/geography/departments")

    assert response.status_code == 200
    assert response.json()["data"] == [
        {"code": "05", "name": "ANTIOQUIA", "is_active": True}
    ]


def test_invalid_department_code_has_stable_error(client, imported_dataset):
    response = client.get(
        "/api/v1/geography/municipalities",
        params={"department_code": "5X"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_DEPARTMENT_CODE"
