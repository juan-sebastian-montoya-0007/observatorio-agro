from pathlib import Path

import pytest

from app.services.importer import (
    WorkbookContractError,
    read_eva_workbook,
    sha256_file,
)


def test_reader_uses_row_9_for_page_and_row_1_for_control(valid_workbook):
    before = set(valid_workbook.parent.iterdir())

    parsed = read_eva_workbook(valid_workbook)

    assert parsed.page.height == 2
    assert parsed.control.height == 1
    assert parsed.notes[0].startswith("Fuente: EVA -UPRA")
    assert parsed.page.columns[0] == "Código Dane departamento"
    assert parsed.control.columns[0] == "codigoDepartamento"
    assert set(valid_workbook.parent.iterdir()) == before


def test_reader_rejects_header_drift_before_returning_rows(workbook_with_changed_header):
    with pytest.raises(WorkbookContractError, match="BasePagina.*Área sembrada") as error:
        read_eva_workbook(workbook_with_changed_header)

    assert error.value.code == "HEADER_MISMATCH"
    assert error.value.sheet == "BasePagina"
    assert error.value.row == 9
    assert error.value.field == "Área sembrada (ha)"


def test_fingerprint_is_stable_and_identifies_file(valid_workbook):
    fingerprint = sha256_file(valid_workbook)

    assert len(fingerprint.sha256) == 64
    assert fingerprint.file_name == "valid.xlsx"
    assert fingerprint == sha256_file(valid_workbook)


@pytest.mark.parametrize(
    ("path_factory", "expected_code"),
    [
        (lambda tmp_path: tmp_path / "missing.xlsx", "FILE_NOT_FOUND"),
        (lambda tmp_path: _corrupt_workbook(tmp_path), "INVALID_WORKBOOK"),
    ],
)
def test_reader_reports_stable_file_errors(tmp_path: Path, path_factory, expected_code):
    with pytest.raises(WorkbookContractError) as error:
        read_eva_workbook(path_factory(tmp_path))

    assert error.value.code == expected_code


def test_reader_reports_missing_required_sheet(workbook_without_control_sheet):
    with pytest.raises(WorkbookContractError) as error:
        read_eva_workbook(workbook_without_control_sheet)

    assert error.value.code == "MISSING_SHEET"
    assert error.value.sheet == "BaseSIPRA"


def _corrupt_workbook(tmp_path: Path) -> Path:
    path = tmp_path / "corrupt.xlsx"
    path.write_bytes(b"not an xlsx archive")
    return path
