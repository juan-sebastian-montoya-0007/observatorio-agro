from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.imports import ImportRepository
from app.services.importer.issues import ImportIssueData, NormalizationError
from app.services.importer.normalizer import NormalizedWorkbook, normalize_workbook
from app.services.importer.reader import read_eva_workbook, sha256_file
from app.services.importer.reconciliation import ReconciliationReport, reconcile_workbook

IMPORTER_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ImportResult:
    status: str
    source_version_id: int
    import_run_id: int
    read_count: int
    inserted_count: int
    warning_count: int
    reused: bool
    reconciliation: ReconciliationReport


class ImportFailed(RuntimeError):
    def __init__(self, code: str, message: str, issues: tuple[ImportIssueData, ...] = ()) -> None:
        self.code = code
        self.issues = issues
        super().__init__(f"{code}: {message}")


class EVAImportService:
    def __init__(self, session: Session, batch_size: int = 1000) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.session = session
        self.batch_size = batch_size
        self.repository = ImportRepository(session)

    def import_file(self, path: Path) -> ImportResult:
        fingerprint = sha256_file(path)
        published = self.repository.published_version(fingerprint.sha256)
        if published is not None:
            run = self.repository.latest_run_for_version(published.id)
            if run is None:
                raise RuntimeError("Published source version has no import run")
            count = self.repository.record_count(published.id)
            return ImportResult(
                status="ALREADY_IMPORTED",
                source_version_id=published.id,
                import_run_id=run.id,
                read_count=count,
                inserted_count=0,
                warning_count=int(run.summary.get("warning_count", 0)),
                reused=True,
                reconciliation=ReconciliationReport(True, count, count, ()),
            )

        parsed = read_eva_workbook(path)
        try:
            normalized = normalize_workbook(parsed)
        except NormalizationError as error:
            coverage = _raw_coverage(parsed.page.get_column("Año").to_list())
            version_id, run_id = self._register(
                fingerprint.sha256,
                fingerprint.file_name,
                coverage,
                parsed.notes,
            )
            primary = next(issue for issue in error.issues if issue.severity == "ERROR")
            self._persist_failure(version_id, run_id, parsed.page.height, primary)
            raise ImportFailed(primary.code, str(error), error.issues) from error

        reconciliation = reconcile_workbook(normalized)
        coverage = _normalized_coverage(normalized)
        version_id, run_id = self._register(
            fingerprint.sha256,
            fingerprint.file_name,
            coverage,
            parsed.notes,
        )

        if not reconciliation.passed:
            mismatch = reconciliation.mismatches[0]
            issue = ImportIssueData(
                severity="ERROR",
                code="RECONCILIATION_MISMATCH",
                sheet="BaseSIPRA",
                row=0,
                field=mismatch.name,
                message=f"{mismatch.key}: difference={mismatch.difference}",
            )
            self._persist_failure(version_id, run_id, normalized.records.height, issue)
            raise ImportFailed(issue.code, issue.message, (issue,))

        try:
            dimensions = self.repository.persist_dimensions(normalized)
            inserted_count = self.repository.insert_records(
                normalized,
                source_version_id=version_id,
                dimensions=dimensions,
                batch_size=self.batch_size,
            )
            self.repository.add_issues(run_id, normalized.issues)
            self.repository.mark_succeeded(
                version_id,
                run_id,
                rows_read=normalized.records.height,
                rows_inserted=inserted_count,
                warning_count=len(normalized.issues),
            )
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            issue = _integrity_issue(error)
            self._persist_failure(version_id, run_id, normalized.records.height, issue)
            raise ImportFailed(issue.code, issue.message, (issue,)) from error
        except Exception:
            self.session.rollback()
            issue = ImportIssueData(
                severity="ERROR",
                code="IMPORT_FAILED",
                sheet="BasePagina",
                row=0,
                field=None,
                message="Unexpected failure while persisting the import",
            )
            self._persist_failure(version_id, run_id, normalized.records.height, issue)
            raise

        return ImportResult(
            status="IMPORTED",
            source_version_id=version_id,
            import_run_id=run_id,
            read_count=normalized.records.height,
            inserted_count=inserted_count,
            warning_count=len(normalized.issues),
            reused=False,
            reconciliation=reconciliation,
        )

    def _register(
        self,
        sha256: str,
        file_name: str,
        coverage: tuple[int, int],
        notes: tuple[str, ...],
    ) -> tuple[int, int]:
        version, run = self.repository.register_attempt(
            sha256=sha256,
            file_name=file_name,
            coverage_start_year=coverage[0],
            coverage_end_year=coverage[1],
            notes=notes,
            importer_version=IMPORTER_VERSION,
        )
        self.session.commit()
        return version.id, run.id

    def _persist_failure(
        self,
        version_id: int,
        run_id: int,
        rows_read: int,
        issue: ImportIssueData,
    ) -> None:
        self.repository.mark_failed(
            version_id,
            run_id,
            rows_read=rows_read,
            issue=issue,
        )
        self.session.commit()


def _normalized_coverage(workbook: NormalizedWorkbook) -> tuple[int, int]:
    years = workbook.records.get_column("year")
    minimum = years.min()
    maximum = years.max()
    if minimum is None or maximum is None:
        raise ImportFailed("EMPTY_WORKBOOK", "BasePagina contains no agricultural records")
    return int(minimum), int(maximum)


def _raw_coverage(values: list[object]) -> tuple[int, int]:
    years = [int(value) for value in values if value is not None and str(value).isdigit()]
    return (min(years), max(years)) if years else (0, 0)


def _integrity_issue(error: IntegrityError) -> ImportIssueData:
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if constraint == "uq_agricultural_record_fact_key":
        code = "DUPLICATE_FACT_KEY"
        message = "The workbook contains an exact duplicate agricultural fact key"
    else:
        code = "INTEGRITY_ERROR"
        message = f"Database integrity constraint failed: {constraint or 'unknown'}"
    return ImportIssueData(
        severity="ERROR",
        code=code,
        sheet="BasePagina",
        row=0,
        field=None,
        message=message,
    )
