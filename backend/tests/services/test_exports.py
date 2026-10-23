import csv
import io
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import load_workbook

import app.services.exports as exports_module
from app.repositories.agriculture import AgricultureRepository
from app.schemas.agriculture import AgriculturalRecordOut
from app.schemas.records import RecordPageQuery, RecordSelectionQuery
from app.services.exports import (
    EXPORT_COLUMNS,
    AgricultureExportService,
    ExportRowLimitExceeded,
)


def export_record(
    record_id: int,
    *,
    department_code: str = "05",
    municipality_code: str = "05001",
    production_t: Decimal = Decimal("18.0000"),
) -> AgriculturalRecordOut:
    return AgriculturalRecordOut(
        id=record_id,
        department_code=department_code,
        department_name="ANTIOQUIA",
        municipality_code=municipality_code,
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
        planted_area_ha=Decimal("10.1250"),
        harvested_area_ha=Decimal("9.0625"),
        production_t=production_t,
        reported_yield_t_ha=Decimal("1.9862068965517241"),
        source_version_id=1,
        source_version_label="2019-2025",
        source_sheet="BasePagina",
        source_row=record_id + 9,
    )


class RepositoryStub:
    def __init__(
        self,
        rows: list[AgriculturalRecordOut],
        *,
        count: int | None = None,
        fail_after: int | None = None,
    ) -> None:
        self.rows = rows
        self.count = len(rows) if count is None else count
        self.fail_after = fail_after
        self.iterated = False
        self.closed = False
        self.batch_sizes: list[int] = []

    def count_records(
        self,
        selection: RecordSelectionQuery,
        source_version_id: int | None,
    ) -> int:
        return self.count

    def iter_records(
        self,
        selection: RecordSelectionQuery,
        batch_size: int,
        source_version_id: int | None,
    ):
        self.iterated = True
        self.batch_sizes.append(batch_size)
        try:
            for index, row in enumerate(self.rows):
                if self.fail_after == index:
                    raise RuntimeError("database stream failed")
                yield row
        finally:
            self.closed = True


def test_csv_streams_header_and_all_rows_in_repository_order_without_numeric_loss():
    rows = [
        export_record(2, production_t=Decimal("1234567890123.1234")),
        export_record(1, department_code="08", municipality_code="08001"),
    ]
    repository = RepositoryStub(rows)
    service = AgricultureExportService(repository, source_version_id=1, batch_size=1)

    chunks = list(service.stream_csv(RecordSelectionQuery(sort_by="production_t")))
    parsed = list(csv.DictReader(io.StringIO("".join(chunks))))

    assert tuple(parsed[0]) == EXPORT_COLUMNS
    assert [row["id"] for row in parsed] == ["2", "1"]
    assert parsed[0]["department_code"] == "05"
    assert parsed[0]["municipality_code"] == "05001"
    assert parsed[0]["production_t"] == "1234567890123.1234"
    assert parsed[0]["reported_yield_t_ha"] == "1.9862068965517241"
    assert repository.batch_sizes == [1]
    assert repository.closed is True


def test_csv_closes_repository_stream_when_consumer_stops_early():
    repository = RepositoryStub([export_record(1), export_record(2)])
    stream = AgricultureExportService(repository, source_version_id=1).stream_csv(
        RecordSelectionQuery()
    )

    next(stream)
    next(stream)
    stream.close()

    assert repository.closed is True


def test_default_hard_limit_rejects_before_iteration_and_never_truncates():
    repository = RepositoryStub([export_record(1)], count=200_001)
    service = AgricultureExportService(repository, source_version_id=1)

    with pytest.raises(ExportRowLimitExceeded) as captured:
        service.ensure_within_limit(RecordSelectionQuery())

    assert captured.value.code == "EXPORT_ROW_LIMIT_EXCEEDED"
    assert captured.value.row_count == 200_001
    assert captured.value.max_rows == 200_000
    assert repository.iterated is False


def test_configured_limit_allows_exact_boundary_and_streams_every_row():
    repository = RepositoryStub([export_record(1), export_record(2)], count=2)
    service = AgricultureExportService(repository, source_version_id=1, max_rows=2)

    assert service.ensure_within_limit(RecordSelectionQuery()) == 2
    parsed = list(csv.DictReader(io.StringIO("".join(service.stream_csv(RecordSelectionQuery())))))

    assert [row["id"] for row in parsed] == ["1", "2"]


def test_service_reuses_pinned_source_version_for_count_and_stream():
    class VersionAwareRepository(RepositoryStub):
        def __init__(self) -> None:
            super().__init__([export_record(1)])
            self.source_versions: list[tuple[str, int | None]] = []

        def count_records(self, selection, source_version_id):
            self.source_versions.append(("count", source_version_id))
            return 1

        def iter_records(self, selection, batch_size, source_version_id):
            self.source_versions.append(("stream", source_version_id))
            yield from self.rows

    repository = VersionAwareRepository()
    service = AgricultureExportService(repository, source_version_id=41)

    assert service.ensure_within_limit(RecordSelectionQuery()) == 1
    assert "".join(service.stream_csv(RecordSelectionQuery()))

    assert repository.source_versions == [("count", 41), ("stream", 41)]


def test_repository_iterator_matches_record_page_order_and_projection(session, fact_factory):
    session.add_all([
        fact_factory(id=2, production_t=Decimal("8.0000"), source_row=11),
        fact_factory(
            id=1,
            crop_variant_id=2,
            production_t=Decimal("9.0000"),
            source_row=10,
        ),
    ])
    session.commit()
    repository = AgricultureRepository(session)
    selection = RecordSelectionQuery(sort_by="production_t", sort_direction="desc")

    streamed = list(repository.iter_records(selection, batch_size=1, source_version_id=1))
    paged = repository.records(
        RecordPageQuery(sort_by="production_t", sort_direction="desc", page_size=100)
    )

    assert streamed == paged.items
    assert repository.count_records(selection, source_version_id=1) == paged.total == 2


def test_repository_iterator_closes_result_when_consumer_stops(monkeypatch):
    class StreamingResult:
        def __init__(self) -> None:
            self.closed = False
            self.requested_batch_size: int | None = None

        def partitions(self, batch_size: int):
            self.requested_batch_size = batch_size
            yield [export_record(1), export_record(2)]

        def close(self) -> None:
            self.closed = True

    class SessionStub:
        def __init__(self, result: StreamingResult) -> None:
            self.result = result

        def execute(self, statement):
            return self.result

    result = StreamingResult()
    repository = AgricultureRepository(SessionStub(result))
    stream = repository.iter_records(
        RecordSelectionQuery(),
        batch_size=17,
        source_version_id=1,
    )

    next(stream)
    stream.close()

    assert result.requested_batch_size == 17
    assert result.closed is True


def test_xlsx_preserves_divipola_as_text_and_decimal_values(tmp_path):
    row = export_record(1, production_t=Decimal("1234567890123.1234"))
    repository = RepositoryStub([row])
    path = AgricultureExportService(
        repository,
        source_version_id=1,
        temp_dir=tmp_path,
    ).build_xlsx(
        RecordSelectionQuery()
    )

    workbook = load_workbook(path, read_only=False, data_only=False)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    values = {header: sheet.cell(row=2, column=index + 1) for index, header in enumerate(headers)}

    assert tuple(headers) == EXPORT_COLUMNS
    assert values["department_code"].value == "05"
    assert values["department_code"].data_type == "s"
    assert values["department_code"].number_format == "@"
    assert values["municipality_code"].value == "05001"
    assert values["municipality_code"].data_type == "s"
    assert values["municipality_code"].number_format == "@"
    assert values["production_t"].value == "1234567890123.1234"
    assert values["production_t"].data_type == "s"
    workbook.close()
    path.unlink()


def test_xlsx_uses_system_temp_directory_by_default():
    repository = RepositoryStub([export_record(1)])
    path = AgricultureExportService(repository, source_version_id=1).build_xlsx(
        RecordSelectionQuery()
    )

    try:
        assert path.parent == Path(tempfile.gettempdir())
        assert path.exists()
    finally:
        path.unlink(missing_ok=True)


def test_xlsx_stream_removes_temporary_file_on_success_and_early_close(tmp_path):
    service = AgricultureExportService(
        RepositoryStub([export_record(1)]),
        source_version_id=1,
        temp_dir=tmp_path,
    )
    completed_path = service.build_xlsx(RecordSelectionQuery())

    assert b"".join(service.stream_xlsx(completed_path))
    assert not completed_path.exists()

    cancelled_path = service.build_xlsx(RecordSelectionQuery())
    stream = service.stream_xlsx(cancelled_path, chunk_size=8)
    assert next(stream)
    stream.close()

    assert not cancelled_path.exists()


def test_xlsx_build_failure_closes_record_stream_and_removes_temporary_file(tmp_path):
    repository = RepositoryStub([export_record(1), export_record(2)], fail_after=1)
    service = AgricultureExportService(repository, source_version_id=1, temp_dir=tmp_path)

    with pytest.raises(RuntimeError, match="database stream failed"):
        service.build_xlsx(RecordSelectionQuery())

    assert repository.closed is True
    assert list(tmp_path.iterdir()) == []


def test_xlsx_constructor_failure_removes_temporary_file(tmp_path, monkeypatch):
    service = AgricultureExportService(
        RepositoryStub([export_record(1)]),
        source_version_id=1,
        temp_dir=tmp_path,
    )

    def fail_workbook_construction(*args, **kwargs):
        raise RuntimeError("workbook construction failed")

    monkeypatch.setattr(exports_module, "Workbook", fail_workbook_construction)

    with pytest.raises(RuntimeError, match="workbook construction failed"):
        service.build_xlsx(RecordSelectionQuery())

    assert list(tmp_path.iterdir()) == []


def test_xlsx_transmission_failure_removes_temporary_file(tmp_path, monkeypatch):
    service = AgricultureExportService(
        RepositoryStub([export_record(1)]),
        source_version_id=1,
        temp_dir=tmp_path,
    )
    path = service.build_xlsx(RecordSelectionQuery())
    real_open = Path.open

    class FailingFile:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size: int) -> bytes:
            raise OSError("client transmission failed")

    def failing_open(file_path: Path, *args, **kwargs):
        if file_path == path:
            return FailingFile()
        return real_open(file_path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)

    with pytest.raises(OSError, match="client transmission failed"):
        next(service.stream_xlsx(path))

    assert not path.exists()
