from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.models import (
    AgriculturalRecord,
    Crop,
    CropGroup,
    CropSubgroup,
    CropVariant,
    Department,
    ImportIssue,
    ImportRun,
    Municipality,
    Period,
    PeriodType,
    PhysicalState,
    Source,
    SourceVersion,
)
from app.services.importer.issues import ImportIssueData
from app.services.importer.normalizer import NormalizedWorkbook


@dataclass(slots=True)
class DimensionIds:
    municipalities: dict[str, int]
    variants: dict[str, int]
    physical_states: dict[str, int]
    periods: dict[tuple[int, str], int]


def latest_run(session: Session) -> ImportRun | None:
    return session.scalar(select(ImportRun).order_by(ImportRun.id.desc()).limit(1))


class ImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def published_version(self, sha256: str) -> SourceVersion | None:
        return self.session.scalar(
            select(SourceVersion).where(
                SourceVersion.sha256 == sha256,
                SourceVersion.status == "PUBLISHED",
            )
        )

    def record_count(self, source_version_id: int) -> int:
        return int(
            self.session.scalar(
                select(func.count(AgriculturalRecord.id)).where(
                    AgriculturalRecord.source_version_id == source_version_id
                )
            )
            or 0
        )

    def latest_run_for_version(self, source_version_id: int) -> ImportRun | None:
        return self.session.scalar(
            select(ImportRun)
            .where(ImportRun.source_version_id == source_version_id)
            .order_by(ImportRun.id.desc())
            .limit(1)
        )

    def register_attempt(
        self,
        *,
        sha256: str,
        file_name: str,
        coverage_start_year: int,
        coverage_end_year: int,
        notes: tuple[str, ...],
        importer_version: str,
    ) -> tuple[SourceVersion, ImportRun]:
        source = self.session.scalar(select(Source).where(Source.name == "EVA"))
        if source is None:
            source = Source(
                name="EVA",
                publisher="UPRA",
                description="Evaluaciones Agropecuarias Municipales",
            )
            self.session.add(source)
            self.session.flush()

        version = self.session.scalar(
            select(SourceVersion).where(SourceVersion.sha256 == sha256)
        )
        if version is None:
            version = SourceVersion(
                source=source,
                version_label=f"{coverage_start_year}-{coverage_end_year}",
                coverage_start_year=coverage_start_year,
                coverage_end_year=coverage_end_year,
                sha256=sha256,
                file_name=file_name,
                notes="\n".join(notes) or None,
                status="STAGED",
            )
            self.session.add(version)
            self.session.flush()
        else:
            version.status = "STAGED"
            version.file_name = file_name
            version.coverage_start_year = coverage_start_year
            version.coverage_end_year = coverage_end_year
            version.notes = "\n".join(notes) or None

        run = ImportRun(
            source_version=version,
            status="RUNNING",
            importer_version=importer_version,
        )
        self.session.add(run)
        self.session.flush()
        return version, run

    def persist_dimensions(self, workbook: NormalizedWorkbook) -> DimensionIds:
        departments = {
            department.code: department
            for department in self.session.scalars(select(Department)).all()
        }
        for row in workbook.dimensions["departments"].iter_rows(named=True):
            if row["department_code"] not in departments:
                department = Department(
                    code=row["department_code"],
                    name=row["department_name"],
                )
                self.session.add(department)
                departments[department.code] = department
        self.session.flush()

        municipalities = {
            municipality.code: municipality
            for municipality in self.session.scalars(select(Municipality)).all()
        }
        for row in workbook.dimensions["municipalities"].iter_rows(named=True):
            if row["municipality_code"] not in municipalities:
                municipality = Municipality(
                    code=row["municipality_code"],
                    name=row["municipality_name"],
                    department_code=row["department_code"],
                )
                self.session.add(municipality)
                municipalities[municipality.code] = municipality
        self.session.flush()

        groups = {
            group.name: group for group in self.session.scalars(select(CropGroup)).all()
        }
        for row in workbook.dimensions["crop_groups"].iter_rows(named=True):
            if row["group"] not in groups:
                group = CropGroup(name=row["group"])
                self.session.add(group)
                groups[group.name] = group
        self.session.flush()

        subgroups = {
            (subgroup.group.name, subgroup.name): subgroup
            for subgroup in self.session.scalars(select(CropSubgroup)).all()
        }
        for row in workbook.dimensions["crop_subgroups"].iter_rows(named=True):
            key = (row["group"], row["subgroup"])
            if key not in subgroups:
                subgroup = CropSubgroup(group=groups[row["group"]], name=row["subgroup"])
                self.session.add(subgroup)
                subgroups[key] = subgroup
        self.session.flush()

        crops = {crop.base_code: crop for crop in self.session.scalars(select(Crop)).all()}
        for row in workbook.dimensions["crops"].iter_rows(named=True):
            if row["crop_base_code"] not in crops:
                crop = Crop(
                    base_code=row["crop_base_code"],
                    name=row["crop_name"],
                    cycle=row["cycle"],
                    group=groups[row["group"]],
                    subgroup=subgroups[(row["group"], row["subgroup"])],
                    general_classification=row["general_classification"],
                )
                self.session.add(crop)
                crops[crop.base_code] = crop
        self.session.flush()

        variants = {
            (
                variant.crop.base_code,
                variant.source_code,
                variant.disaggregation,
                variant.scientific_name,
            ): variant
            for variant in self.session.scalars(select(CropVariant)).all()
        }
        variant_ids: dict[str, int] = {}
        for row in workbook.dimensions["crop_variants"].iter_rows(named=True):
            key = (
                row["crop_base_code"],
                row["crop_source_code"],
                row["crop_disaggregation"],
                row["scientific_name"],
            )
            variant = variants.get(key)
            if variant is None:
                variant = CropVariant(
                    crop=crops[row["crop_base_code"]],
                    source_code=row["crop_source_code"],
                    disaggregation=row["crop_disaggregation"],
                    scientific_name=row["scientific_name"],
                )
                self.session.add(variant)
                variants[key] = variant
            self.session.flush()
            variant_ids[row["variant_key"]] = variant.id

        physical_states = {
            state.name: state
            for state in self.session.scalars(select(PhysicalState)).all()
        }
        for row in workbook.dimensions["physical_states"].iter_rows(named=True):
            if row["physical_state"] not in physical_states:
                state = PhysicalState(name=row["physical_state"])
                self.session.add(state)
                physical_states[state.name] = state
        self.session.flush()

        periods = {
            (period.year, period.period_type.value): period
            for period in self.session.scalars(select(Period)).all()
        }
        for row in workbook.dimensions["periods"].iter_rows(named=True):
            key = (row["year"], row["period_type"])
            if key not in periods:
                period = Period(
                    year=row["year"],
                    period_type=PeriodType(row["period_type"]),
                    original_label=row["period_label"],
                    chronological_order=row["chronological_order"],
                )
                self.session.add(period)
                periods[key] = period
        self.session.flush()

        return DimensionIds(
            municipalities={code: item.id for code, item in municipalities.items()},
            variants=variant_ids,
            physical_states={name: item.id for name, item in physical_states.items()},
            periods={(year, kind): item.id for (year, kind), item in periods.items()},
        )

    def insert_records(
        self,
        workbook: NormalizedWorkbook,
        *,
        source_version_id: int,
        dimensions: DimensionIds,
        batch_size: int,
    ) -> int:
        rows = workbook.records.iter_rows(named=True)
        inserted = 0
        for batch in _batched(rows, batch_size):
            payload = [
                {
                    "source_version_id": source_version_id,
                    "municipality_id": dimensions.municipalities[row["municipality_code"]],
                    "crop_variant_id": dimensions.variants[row["variant_key"]],
                    "period_id": dimensions.periods[(row["year"], row["period_type"])],
                    "physical_state_id": dimensions.physical_states[row["physical_state"]],
                    "planted_area_ha": row["planted_area_ha"],
                    "harvested_area_ha": row["harvested_area_ha"],
                    "production_t": row["production_t"],
                    "reported_yield_t_ha": row["reported_yield_t_ha"],
                    "source_row": row["source_row"],
                    "trace_metadata": {"sheet": "BasePagina", "row": row["source_row"]},
                }
                for row in batch
            ]
            self.session.execute(insert(AgriculturalRecord), payload)
            inserted += len(payload)
        return inserted

    def add_issues(self, import_run_id: int, issues: Iterable[ImportIssueData]) -> None:
        self.session.add_all(
            [
                ImportIssue(
                    import_run_id=import_run_id,
                    severity=issue.severity,
                    sheet=issue.sheet,
                    row=issue.row,
                    field=issue.field,
                    code=issue.code,
                    message=issue.message,
                )
                for issue in issues
            ]
        )

    def mark_succeeded(
        self,
        source_version_id: int,
        import_run_id: int,
        *,
        rows_read: int,
        rows_inserted: int,
        warning_count: int,
    ) -> None:
        version = self.session.get(SourceVersion, source_version_id)
        run = self.session.get(ImportRun, import_run_id)
        if version is None or run is None:
            raise RuntimeError("Import attempt disappeared before completion")
        version.status = "PUBLISHED"
        run.status = "SUCCEEDED"
        run.finished_at = datetime.now(UTC)
        run.rows_read = rows_read
        run.rows_inserted = rows_inserted
        run.rows_rejected = 0
        run.summary = {"warning_count": warning_count}

    def mark_failed(
        self,
        source_version_id: int,
        import_run_id: int,
        *,
        rows_read: int,
        issue: ImportIssueData,
    ) -> None:
        version = self.session.get(SourceVersion, source_version_id)
        run = self.session.get(ImportRun, import_run_id)
        if version is None or run is None:
            raise RuntimeError("Import attempt disappeared before failure could be recorded")
        version.status = "FAILED"
        run.status = "FAILED"
        run.finished_at = datetime.now(UTC)
        run.rows_read = rows_read
        run.rows_inserted = 0
        run.rows_rejected = rows_read
        run.summary = {"failure_code": issue.code}
        self.add_issues(import_run_id, (issue,))


def _batched(rows: Iterable[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
