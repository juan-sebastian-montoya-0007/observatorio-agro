from __future__ import annotations

import csv
import io
import tempfile
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

from app.repositories.agriculture import AgricultureRepository
from app.schemas.agriculture import AgriculturalRecordOut
from app.schemas.records import RecordSelectionQuery

EXPORT_COLUMNS = tuple(AgriculturalRecordOut.model_fields)
DIVIPOLA_COLUMNS = frozenset({"department_code", "municipality_code"})


class ExportRowLimitExceeded(Exception):
    code = "EXPORT_ROW_LIMIT_EXCEEDED"

    def __init__(self, row_count: int, max_rows: int) -> None:
        self.row_count = row_count
        self.max_rows = max_rows
        super().__init__(f"export has {row_count} rows; maximum is {max_rows}")


class AgricultureExportService:
    def __init__(
        self,
        repository: AgricultureRepository,
        *,
        source_version_id: int | None,
        max_rows: int = 200_000,
        batch_size: int = 1_000,
        temp_dir: Path | None = None,
    ) -> None:
        if max_rows < 1:
            raise ValueError("max_rows must be positive")
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.repository = repository
        self.source_version_id = source_version_id
        self.max_rows = max_rows
        self.batch_size = batch_size
        self.temp_dir = temp_dir

    def ensure_within_limit(self, selection: RecordSelectionQuery) -> int:
        row_count = self.repository.count_records(selection, self.source_version_id)
        if row_count > self.max_rows:
            raise ExportRowLimitExceeded(row_count, self.max_rows)
        return row_count

    def stream_csv(self, selection: RecordSelectionQuery) -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(EXPORT_COLUMNS)
        yield self._take_buffer(buffer)

        records = self.repository.iter_records(
            selection,
            self.batch_size,
            self.source_version_id,
        )
        try:
            for record in records:
                data = record.model_dump(mode="python")
                writer.writerow([self._csv_value(data[column]) for column in EXPORT_COLUMNS])
                yield self._take_buffer(buffer)
        finally:
            close = getattr(records, "close", None)
            if close is not None:
                close()

    def build_xlsx(self, selection: RecordSelectionQuery) -> Path:
        workbook = Workbook(write_only=True)
        worksheet = None
        path = None
        records = None
        try:
            worksheet = workbook.create_sheet("Registros")
            temporary = tempfile.NamedTemporaryFile(
                prefix="agriculture-export-",
                suffix=".xlsx",
                dir=self.temp_dir,
                delete=False,
            )
            path = Path(temporary.name)
            temporary.close()
            records = self.repository.iter_records(
                selection,
                self.batch_size,
                self.source_version_id,
            )
            worksheet.append(EXPORT_COLUMNS)
            for record in records:
                data = record.model_dump(mode="python")
                worksheet.append([
                    self._xlsx_value(worksheet, column, data[column])
                    for column in EXPORT_COLUMNS
                ])
            workbook.save(path)
            return path
        except BaseException:
            if worksheet is not None:
                try:
                    worksheet.close()
                except Exception:
                    pass
            if path is not None:
                path.unlink(missing_ok=True)
            raise
        finally:
            if records is not None:
                close = getattr(records, "close", None)
                if close is not None:
                    close()
            workbook.close()

    @staticmethod
    def stream_xlsx(path: Path, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        try:
            with path.open("rb") as workbook:
                while chunk := workbook.read(chunk_size):
                    yield chunk
        finally:
            path.unlink(missing_ok=True)

    @staticmethod
    def _take_buffer(buffer: io.StringIO) -> str:
        value = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return value

    @staticmethod
    def _csv_value(value: object) -> object:
        return "" if value is None else value

    @staticmethod
    def _xlsx_value(worksheet, column: str, value: object):
        if isinstance(value, Decimal):
            return str(value)
        if column not in DIVIPOLA_COLUMNS:
            return value
        cell = WriteOnlyCell(worksheet, value=str(value))
        cell.number_format = "@"
        return cell
