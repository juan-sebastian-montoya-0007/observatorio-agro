import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import AgriculturalRecord
from app.services.importer.import_service import EVAImportService
from app.services.importer.reader import sha256_file

EXPECTED_SHA256 = "355e70a7a5b8f3ce76f26f97463f77c24d4c5e63abd7b28c9b6395a1f65854b0"


@pytest.fixture
def source_path() -> Path:
    configured = os.getenv("EVA_SOURCE_XLSX")
    if not configured:
        pytest.skip("EVA_SOURCE_XLSX is not configured; full source test is opt-in")
    path = Path(configured)
    if not path.is_file():
        pytest.skip(f"EVA_SOURCE_XLSX does not exist: {path}")
    fingerprint = sha256_file(path)
    assert fingerprint.sha256 == EXPECTED_SHA256, "supplied workbook fingerprint changed"
    return path


@pytest.mark.full_source
def test_supplied_workbook_reconciles_and_imports(source_path, session):
    result = EVAImportService(session).import_file(source_path)

    assert result.read_count == 166_733
    assert result.inserted_count == 166_733
    assert result.reconciliation.page_rows == 151_312
    assert result.reconciliation.control_rows == 151_312
    assert result.reconciliation.passed is True
    assert result.warning_count >= 13_208
    assert session.scalar(
        select(func.count(AgriculturalRecord.id)).where(
            AgriculturalRecord.source_version_id == result.source_version_id
        )
    ) == 166_733
