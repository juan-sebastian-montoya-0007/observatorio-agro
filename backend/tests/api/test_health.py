def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_exposes_download_filename_header(client):
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-expose-headers"] == "Content-Disposition"
