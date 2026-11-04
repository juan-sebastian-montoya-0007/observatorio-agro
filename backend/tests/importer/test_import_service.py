import pytest
from sqlalchemy import func, select

from app.models import AgriculturalRecord, ImportRun, Source, SourceVersion
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


def test_new_import_records_only_verified_source_metadata(session, valid_workbook):
    EVAImportService(session).import_file(valid_workbook)

    source = session.scalar(select(Source))

    assert source is not None
    assert source.name == "Evaluaciones Agropecuarias Municipales (EVA)"
    assert source.publisher == "UPRA"
    assert source.description == (
        "Evaluaciones Agropecuarias Municipales (EVA), publicadas por la UPRA."
    )
    assert source.official_url == "https://upra.gov.co/es-co/eva/eva-2025"
    assert source.reuse_terms is None


def test_reimport_backfills_only_source_metadata_before_already_imported(
    session,
    valid_workbook,
):
    first = EVAImportService(session).import_file(valid_workbook)
    source = session.get(Source, session.get(SourceVersion, first.source_version_id).source_id)
    assert source is not None
    source.name = "EVA"
    source.publisher = "EDITOR DESCONOCIDO"
    source.description = None
    source.official_url = None
    source.reuse_terms = "Términos no verificados"
    session.commit()

    version_before = session.execute(
        select(
            SourceVersion.id,
            SourceVersion.source_id,
            SourceVersion.version_label,
            SourceVersion.coverage_start_year,
            SourceVersion.coverage_end_year,
            SourceVersion.available_date,
            SourceVersion.sha256,
            SourceVersion.file_name,
            SourceVersion.notes,
            SourceVersion.status,
            SourceVersion.created_at,
        ).where(SourceVersion.id == first.source_version_id)
    ).one()
    facts_before = session.execute(
        select(
            AgriculturalRecord.id,
            AgriculturalRecord.source_version_id,
            AgriculturalRecord.municipality_id,
            AgriculturalRecord.crop_variant_id,
            AgriculturalRecord.period_id,
            AgriculturalRecord.physical_state_id,
            AgriculturalRecord.planted_area_ha,
            AgriculturalRecord.harvested_area_ha,
            AgriculturalRecord.production_t,
            AgriculturalRecord.reported_yield_t_ha,
            AgriculturalRecord.source_row,
            AgriculturalRecord.trace_metadata,
        ).order_by(AgriculturalRecord.id)
    ).all()
    run_count_before = session.scalar(select(func.count(ImportRun.id)))

    second = EVAImportService(session).import_file(valid_workbook)

    session.expire_all()
    source = session.get(Source, source.id)
    version_after = session.execute(
        select(
            SourceVersion.id,
            SourceVersion.source_id,
            SourceVersion.version_label,
            SourceVersion.coverage_start_year,
            SourceVersion.coverage_end_year,
            SourceVersion.available_date,
            SourceVersion.sha256,
            SourceVersion.file_name,
            SourceVersion.notes,
            SourceVersion.status,
            SourceVersion.created_at,
        ).where(SourceVersion.id == first.source_version_id)
    ).one()
    facts_after = session.execute(
        select(
            AgriculturalRecord.id,
            AgriculturalRecord.source_version_id,
            AgriculturalRecord.municipality_id,
            AgriculturalRecord.crop_variant_id,
            AgriculturalRecord.period_id,
            AgriculturalRecord.physical_state_id,
            AgriculturalRecord.planted_area_ha,
            AgriculturalRecord.harvested_area_ha,
            AgriculturalRecord.production_t,
            AgriculturalRecord.reported_yield_t_ha,
            AgriculturalRecord.source_row,
            AgriculturalRecord.trace_metadata,
        ).order_by(AgriculturalRecord.id)
    ).all()

    assert second.status == "ALREADY_IMPORTED"
    assert source is not None
    assert source.name == "Evaluaciones Agropecuarias Municipales (EVA)"
    assert source.publisher == "UPRA"
    assert source.description == (
        "Evaluaciones Agropecuarias Municipales (EVA), publicadas por la UPRA."
    )
    assert source.official_url == "https://upra.gov.co/es-co/eva/eva-2025"
    assert source.reuse_terms is None
    assert version_after == version_before
    assert facts_after == facts_before
    assert session.scalar(select(func.count(AgriculturalRecord.id))) == 2
    assert session.scalar(select(func.count(SourceVersion.id))) == 1
    assert session.scalar(select(func.count(ImportRun.id))) == run_count_before == 1


def test_failed_batch_leaves_no_partial_facts(session, duplicate_key_workbook):
    with pytest.raises(ImportFailed, match="DUPLICATE_FACT_KEY"):
        EVAImportService(session, batch_size=1).import_file(duplicate_key_workbook)

    assert session.scalar(select(func.count(AgriculturalRecord.id))) == 0
    run = latest_run(session)
    assert isinstance(run, ImportRun)
    assert run.status == "FAILED"
    assert run.rows_inserted == 0
    assert [issue.code for issue in run.issues] == ["DUPLICATE_FACT_KEY"]
