from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from zipfile import BadZipFile

import polars as pl
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.worksheet import Worksheet

from app.services.importer.contracts import (
    ParsedWorkbook,
    WorkbookContractError,
    WorkbookFingerprint,
)
from app.services.importer.source_contract import (
    BASE_PAGINA_HEADER_ROW,
    BASE_PAGINA_HEADERS,
    BASE_PAGINA_SHEET,
    BASE_SIPRA_HEADER_ROW,
    BASE_SIPRA_HEADERS,
    BASE_SIPRA_SHEET,
)

_READ_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> WorkbookFingerprint:
    source_path = Path(path)
    digest = sha256()
    try:
        with source_path.open("rb") as source:
            while chunk := source.read(_READ_CHUNK_SIZE):
                digest.update(chunk)
    except FileNotFoundError as error:
        raise WorkbookContractError(
            "FILE_NOT_FOUND", f"Workbook does not exist: {source_path}"
        ) from error
    except OSError as error:
        raise WorkbookContractError(
            "FILE_UNREADABLE", f"Workbook cannot be read: {source_path}"
        ) from error

    return WorkbookFingerprint(sha256=digest.hexdigest(), file_name=source_path.name)


def read_eva_workbook(path: Path) -> ParsedWorkbook:
    source_path = Path(path)
    if not source_path.is_file():
        raise WorkbookContractError(
            "FILE_NOT_FOUND", f"Workbook does not exist: {source_path}"
        )

    try:
        workbook = load_workbook(source_path, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as error:
        raise WorkbookContractError(
            "INVALID_WORKBOOK", f"Workbook is not a readable XLSX file: {source_path.name}"
        ) from error

    try:
        page_sheet = _required_sheet(workbook.sheetnames, workbook, BASE_PAGINA_SHEET)
        control_sheet = _required_sheet(workbook.sheetnames, workbook, BASE_SIPRA_SHEET)

        _validate_headers(
            page_sheet,
            sheet_name=BASE_PAGINA_SHEET,
            header_row=BASE_PAGINA_HEADER_ROW,
            expected=BASE_PAGINA_HEADERS,
        )
        _validate_headers(
            control_sheet,
            sheet_name=BASE_SIPRA_SHEET,
            header_row=BASE_SIPRA_HEADER_ROW,
            expected=BASE_SIPRA_HEADERS,
        )

        notes = _read_notes(page_sheet)
        page_rows = _read_rows(page_sheet, BASE_PAGINA_HEADER_ROW + 1, len(BASE_PAGINA_HEADERS))
        control_rows = _read_rows(
            control_sheet,
            BASE_SIPRA_HEADER_ROW + 1,
            len(BASE_SIPRA_HEADERS),
        )
    finally:
        workbook.close()

    return ParsedWorkbook(
        page=_to_dataframe(page_rows, BASE_PAGINA_HEADERS),
        control=_to_dataframe(control_rows, BASE_SIPRA_HEADERS),
        notes=notes,
    )


def _required_sheet(sheet_names: list[str], workbook, sheet_name: str) -> Worksheet:
    if sheet_name not in sheet_names:
        raise WorkbookContractError(
            "MISSING_SHEET",
            f"Required worksheet is missing: {sheet_name}",
            sheet=sheet_name,
        )
    return workbook[sheet_name]


def _validate_headers(
    worksheet: Worksheet,
    *,
    sheet_name: str,
    header_row: int,
    expected: tuple[str, ...],
) -> None:
    values = next(
        worksheet.iter_rows(
            min_row=header_row,
            max_row=header_row,
            max_col=len(expected),
            values_only=True,
        )
    )
    actual = tuple(values)
    if actual == expected:
        return

    mismatch_index = next(
        (
            index
            for index, (found, wanted) in enumerate(zip(actual, expected, strict=False))
            if found != wanted
        ),
        min(len(actual), len(expected)),
    )
    wanted = expected[mismatch_index] if mismatch_index < len(expected) else "<no extra field>"
    found = actual[mismatch_index] if mismatch_index < len(actual) else "<missing>"
    raise WorkbookContractError(
        "HEADER_MISMATCH",
        f"{sheet_name} expected {wanted!r} but found {found!r}",
        sheet=sheet_name,
        row=header_row,
        field=wanted,
    )


def _read_notes(worksheet: Worksheet) -> tuple[str, ...]:
    notes: list[str] = []
    for (value,) in worksheet.iter_rows(
        min_row=1,
        max_row=BASE_PAGINA_HEADER_ROW - 1,
        min_col=1,
        max_col=1,
        values_only=True,
    ):
        if isinstance(value, str):
            note = value.strip()
            if note.startswith(("Fuente:", "*")):
                notes.append(note)
    return tuple(notes)


def _read_rows(worksheet: Worksheet, first_row: int, width: int) -> list[tuple[object, ...]]:
    return [
        tuple(row)
        for row in worksheet.iter_rows(
            min_row=first_row,
            max_col=width,
            values_only=True,
        )
        if any(value is not None for value in row)
    ]


def _to_dataframe(rows: list[tuple[object, ...]], headers: tuple[str, ...]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(schema={header: pl.Null for header in headers})
    return pl.DataFrame(rows, schema=list(headers), orient="row", strict=False)
