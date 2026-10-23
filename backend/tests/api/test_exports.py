import asyncio
import csv
import io
import tempfile
from decimal import Decimal
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

import app.api.v1.exports as exports_api
import app.services.exports as exports_service
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.schemas.agriculture import AgriculturalRecordOut


def api_record(record_id: int) -> AgriculturalRecordOut:
    return AgriculturalRecordOut(
        id=record_id,
        department_code="05",
        department_name="ANTIOQUIA",
        municipality_code="05001",
        municipality_name="MEDELLÍN",
        year=2024,
        period_type="ANNUAL",
        crop_id=1,
        crop_base_code="10807",
        crop_name="PAPA",
        crop_variant_id=1,
        crop_variant_source_code="1080701",
        crop_variant_disaggregation="PAPA CRIOLLA",
        physical_state="EN FRESCO",
        planted_area_ha=Decimal("10.0000"),
        harvested_area_ha=Decimal("9.0000"),
        production_t=Decimal("18.0000"),
        reported_yield_t_ha=Decimal("2.0000"),
        source_version_id=1,
        source_version_label="2019-2025",
        source_sheet="BasePagina",
        source_row=record_id + 9,
    )


class RepositoryStub:
    def __init__(self, rows: list[AgriculturalRecordOut]) -> None:
        self.rows = rows
        self.closed = False
        self.selection = None

    @staticmethod
    def latest_published_version():
        return type("Version", (), {"id": 1})()

    def count_records(self, selection, source_version_id) -> int:
        self.selection = selection
        return len(self.rows)

    def iter_records(self, selection, batch_size, source_version_id):
        self.selection = selection
        try:
            yield from self.rows
        finally:
            self.closed = True


def test_csv_export_has_download_headers_and_reuses_filter_search_and_order(
    client, session, fact_factory
):
    session.add_all([
        fact_factory(
            id=1,
            crop_variant_id=2,
            production_t=Decimal("36.1250"),
            source_row=11,
        ),
        fact_factory(id=2, production_t=Decimal("18.0000"), source_row=10),
    ])
    session.commit()

    response = client.get(
        "/api/v1/exports/agriculture",
        params={
            "format": "csv",
            "department": "05",
            "municipality": "05001",
            "search": "PAPA",
            "sort_by": "production_t",
            "sort_direction": "desc",
        },
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == (
        'attachment; filename="agriculture-records.csv"'
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-expose-headers"] == "Content-Disposition"
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert [row["id"] for row in rows] == ["1", "2"]
    assert rows[0]["department_code"] == "05"
    assert rows[0]["municipality_code"] == "05001"
    assert rows[0]["production_t"] == "36.1250"


def test_xlsx_export_has_download_headers_and_text_divipola(client, fact_factory, session):
    session.add(fact_factory(id=1))
    session.commit()

    response = client.get("/api/v1/exports/agriculture", params={"format": "xlsx"})

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="agriculture-records.xlsx"'
    )
    workbook = load_workbook(io.BytesIO(response.content), read_only=False)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    values = {header: sheet.cell(row=2, column=index + 1) for index, header in enumerate(headers)}
    assert values["department_code"].value == "05"
    assert values["department_code"].number_format == "@"
    assert values["municipality_code"].value == "05001"
    assert values["municipality_code"].number_format == "@"
    workbook.close()


def test_export_rejects_invalid_format(client):
    response = client.get("/api/v1/exports/agriculture", params={"format": "pdf"})

    assert response.status_code == 422


def test_export_limit_returns_stable_413_before_response_stream(session, fact_factory):
    session.add_all([
        fact_factory(id=1),
        fact_factory(id=2, crop_variant_id=2, source_row=11),
    ])
    session.commit()
    application = create_app(Settings(export_max_rows=1))

    def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as test_client:
        response = test_client.get(
            "/api/v1/exports/agriculture",
            params={"format": "csv"},
        )

    assert response.status_code == 413
    assert response.json() == {
        "detail": {
            "code": "EXPORT_ROW_LIMIT_EXCEEDED",
            "message": "La exportación supera el límite de filas permitido.",
            "row_count": 2,
            "max_rows": 1,
        }
    }
    assert "content-disposition" not in response.headers


def test_export_pins_latest_version_once_before_count_and_stream(monkeypatch):
    class SwitchingRepository:
        def __init__(self) -> None:
            self.latest_id = 7
            self.latest_calls = 0
            self.source_versions: list[tuple[str, int | None]] = []

        def latest_published_version(self):
            self.latest_calls += 1
            return type("Version", (), {"id": self.latest_id})()

        def count_records(self, selection, source_version_id):
            self.source_versions.append(("count", source_version_id))
            self.latest_id = 8
            return 1

        def iter_records(self, selection, batch_size, source_version_id):
            self.source_versions.append(("stream", source_version_id))
            yield api_record(1)

    repository = SwitchingRepository()
    application = create_app()

    def override_session():
        yield object()

    application.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(exports_api, "AgricultureRepository", lambda session: repository)

    with TestClient(application) as test_client:
        response = test_client.get(
            "/api/v1/exports/agriculture",
            params={"format": "csv"},
        )

    assert response.status_code == 200
    assert repository.latest_calls == 1
    assert repository.source_versions == [("count", 7), ("stream", 7)]


def test_csv_asgi_cancellation_closes_real_cursor_and_request_session(
    session, fact_factory, monkeypatch
):
    session.add_all([
        fact_factory(id=1),
        fact_factory(id=2, crop_variant_id=2, source_row=11),
    ])
    session.commit()
    application = create_app()
    request_session_closed = False
    streaming_results = []
    execute = session.execute
    close = session.close

    def capture_execute(statement, *args, **kwargs):
        result = execute(statement, *args, **kwargs)
        if statement.get_execution_options().get("stream_results"):
            streaming_results.append(result)
        return result

    def capture_close():
        nonlocal request_session_closed
        request_session_closed = True
        close()

    def override_session():
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(session, "execute", capture_execute)
    monkeypatch.setattr(session, "close", capture_close)
    application.dependency_overrides[get_session] = override_session
    messages = []

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            cancel_streaming_request(
                application,
                "/api/v1/exports/agriculture?format=csv",
                cancel_on_body=2,
                messages=messages,
            )
        )

    assert messages[-1]["type"] == "http.response.body"
    assert messages[-1]["more_body"] is True
    assert len(streaming_results) == 1
    assert streaming_results[0].closed is True
    assert request_session_closed is True


def test_xlsx_asgi_cancellation_removes_temp_and_closes_request_session(
    monkeypatch, tmp_path
):
    repository = RepositoryStub([api_record(1)])
    application = create_app()
    request_session_closed = False
    real_named_temporary_file = tempfile.NamedTemporaryFile

    def override_session():
        nonlocal request_session_closed
        try:
            yield object()
        finally:
            request_session_closed = True

    def local_named_temporary_file(**kwargs):
        return real_named_temporary_file(**(kwargs | {"dir": tmp_path}))

    application.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(exports_api, "AgricultureRepository", lambda session: repository)
    monkeypatch.setattr(
        exports_service.tempfile,
        "NamedTemporaryFile",
        local_named_temporary_file,
    )
    messages = []

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            cancel_streaming_request(
                application,
                "/api/v1/exports/agriculture?format=xlsx",
                cancel_on_body=1,
                messages=messages,
            )
        )

    assert messages[-1]["type"] == "http.response.body"
    assert messages[-1]["more_body"] is True
    assert repository.closed is True
    assert request_session_closed is True
    assert list(tmp_path.iterdir()) == []


async def cancel_streaming_request(
    application,
    url: str,
    *,
    cancel_on_body: int,
    messages: list[dict],
):
    parsed = urlsplit(url)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("ascii"),
        "query_string": parsed.query.encode("ascii"),
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "state": {},
    }
    body_messages = 0

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal body_messages
        messages.append(message)
        if message["type"] == "http.response.body" and message.get("body"):
            body_messages += 1
            if body_messages == cancel_on_body:
                raise asyncio.CancelledError

    await application(scope, receive, send)
    return messages
