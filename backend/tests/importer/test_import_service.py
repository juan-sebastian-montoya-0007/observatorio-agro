import pytest
from sqlalchemy import func, select

from app.models import AgriculturalRecord, ImportRun, SourceVersion
from app.repositories.imports import latest_run
from app.services.importer.import_service import EVAImportService, ImportFailed


def test_import_is_idempotent_by_sha256(session, valid_workbook):
    first = EVAImportService(session).import_file(valid_workbook)
    second = EVAImportService(session).import_file(valid_workbook)

    assert first.status == "IMPORTED"
    assert first.inserted_count == 2
    assert second.status == "ALREADY_IMPORTED"
    assert second.reused is True
    assert second.inserted_count == 0
    assert session.scalar(select(func.count(AgriculturalRecord.id))) == 2
    assert session.scalar(select(func.count(SourceVersion.id))) == 1


def test_failed_batch_leaves_no_partial_facts(session, duplicate_key_workbook):
    with pytest.raises(ImportFailed, match="DUPLICATE_FACT_KEY"):
        EVAImportService(session, batch_size=1).import_file(duplicate_key_workbook)

    assert session.scalar(select(func.count(AgriculturalRecord.id))) == 0
    run = latest_run(session)
    assert isinstance(run, ImportRun)
    assert run.status == "FAILED"
    assert run.rows_inserted == 0
    assert [issue.code for issue in run.issues] == ["DUPLICATE_FACT_KEY"]
