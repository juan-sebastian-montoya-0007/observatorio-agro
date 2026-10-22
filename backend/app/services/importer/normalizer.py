from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import polars as pl

from app.models import PeriodType
from app.services.importer.contracts import ParsedWorkbook
from app.services.importer.issues import ImportIssueData, NormalizationError

_PERIOD_PATTERN = re.compile(r"^(?P<year>\d{4})(?P<suffix>[AB]?)$")
_RECORD_COLUMNS = (
    "source_row",
    "department_code",
    "department_name",
    "municipality_code",
    "municipality_name",
    "crop_base_code",
    "crop_source_code",
    "crop_name",
    "crop_disaggregation",
    "cycle",
    "group",
    "subgroup",
    "general_classification",
    "year",
    "period_type",
    "period_label",
    "chronological_order",
    "planted_area_ha",
    "harvested_area_ha",
    "production_t",
    "reported_yield_t_ha",
    "scientific_name",
    "physical_state",
    "variant_key",
)


@dataclass(frozen=True, slots=True)
class NormalizedWorkbook:
    records: pl.DataFrame
    control_rows: pl.DataFrame
    dimensions: dict[str, pl.DataFrame]
    issues: tuple[ImportIssueData, ...]


class _PeriodError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def parse_period(year: int, label: str) -> tuple[int, PeriodType]:
    try:
        parsed_year = int(year)
    except (TypeError, ValueError) as error:
        raise _PeriodError("INVALID_PERIOD", f"Invalid year: {year!r}") from error

    normalized_label = _text(label).upper().replace(" ", "")
    match = _PERIOD_PATTERN.fullmatch(normalized_label)
    if match is None:
        raise _PeriodError("INVALID_PERIOD", f"Invalid period label: {label!r}")
    if int(match.group("year")) != parsed_year:
        raise _PeriodError(
            "PERIOD_MISMATCH",
            f"Period {normalized_label!r} does not match year {parsed_year}",
        )

    period_type = {
        "": PeriodType.ANNUAL,
        "A": PeriodType.SEMESTER_A,
        "B": PeriodType.SEMESTER_B,
    }[match.group("suffix")]
    return parsed_year, period_type


def normalize_workbook(parsed: ParsedWorkbook) -> NormalizedWorkbook:
    issues: list[ImportIssueData] = []
    control_rows, crop_mapping = _normalize_control(parsed.control, issues)
    records = _normalize_page(parsed.page, crop_mapping, issues)

    if any(issue.severity == "ERROR" for issue in issues):
        raise NormalizationError(tuple(issues))

    records_frame = _frame(records, _RECORD_COLUMNS)
    control_frame = _frame(control_rows, _control_columns())
    return NormalizedWorkbook(
        records=records_frame,
        control_rows=control_frame,
        dimensions=_dimensions(records_frame),
        issues=tuple(issues),
    )


def _normalize_control(
    frame: pl.DataFrame,
    issues: list[ImportIssueData],
) -> tuple[list[dict[str, Any]], dict[tuple[str, ...], tuple[str, str]]]:
    normalized: list[dict[str, Any]] = []
    mapping_candidates: dict[tuple[str, ...], set[tuple[str, str]]] = {}

    for offset, raw in enumerate(frame.iter_rows(named=True), start=2):
        row_issues_before = len(issues)
        department_code = _divipola(raw["codigoDepartamento"], 2, "BaseSIPRA", offset, issues)
        municipality_code = _divipola(raw["codigoMunicipio"], 5, "BaseSIPRA", offset, issues)
        _validate_territorial_parent(
            department_code,
            municipality_code,
            "BaseSIPRA",
            offset,
            issues,
        )
        year, period_type = _period(raw["anho"], raw["Periodo"], "BaseSIPRA", offset, issues)
        metrics = _metrics(
            raw,
            {
                "planted_area_ha": "AreaSembrada",
                "harvested_area_ha": "AreaCosechada",
                "production_t": "produccio",
                "reported_yield_t_ha": "rendimiento",
            },
            "BaseSIPRA",
            offset,
            issues,
        )
        crop_base_code = _digit_code(raw["cod_cultiv"], "cod_cultiv", "BaseSIPRA", offset, issues)
        if any(issue.severity == "ERROR" for issue in issues[row_issues_before:]):
            continue

        values = {
            "source_row": offset,
            "department_code": department_code,
            "department_name": _text(raw["departamento"]),
            "municipality_code": municipality_code,
            "municipality_name": _text(raw["municipio"]),
            "crop_base_code": crop_base_code,
            "crop_name": _text(raw["especie"]),
            "cycle": _text(raw["nombre_tipo_ciclo"]),
            "group": _text(raw["grupo_especie"]),
            "subgroup": _text(raw["subGrupo_Especie"]),
            "general_classification": _text(raw["Clasifica_grupo"]),
            "year": year,
            "period_type": period_type.value,
            "period_label": _text(raw["Periodo"]).upper().replace(" ", ""),
            "chronological_order": _chronological_order(year, period_type),
            **metrics,
            "scientific_name": _text(raw["nombre_cientifico"]),
            "physical_state": _text(raw["EstadoFisicoProduccio"]),
        }
        normalized.append(values)
        mapping_key = _crop_mapping_key(values)
        mapping_candidates.setdefault(mapping_key, set()).add(
            (crop_base_code, values["general_classification"])
        )

    mapping: dict[tuple[str, ...], tuple[str, str]] = {}
    for key, candidates in mapping_candidates.items():
        if len(candidates) > 1:
            issues.append(
                ImportIssueData(
                    severity="ERROR",
                    code="AMBIGUOUS_BASE_CROP",
                    sheet="BaseSIPRA",
                    row=0,
                    field="cod_cultiv",
                    message=f"Shared crop key maps to multiple base crops: {sorted(candidates)!r}",
                )
            )
            continue
        mapping[key] = next(iter(candidates))

    return normalized, mapping


def _normalize_page(
    frame: pl.DataFrame,
    crop_mapping: dict[tuple[str, ...], tuple[str, str]],
    issues: list[ImportIssueData],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for offset, raw in enumerate(frame.iter_rows(named=True), start=10):
        row_issues_before = len(issues)
        department_code = _divipola(
            raw["Código Dane departamento"], 2, "BasePagina", offset, issues
        )
        municipality_code = _divipola(
            raw["Código Dane municipio"], 5, "BasePagina", offset, issues
        )
        _validate_territorial_parent(
            department_code,
            municipality_code,
            "BasePagina",
            offset,
            issues,
        )
        year, period_type = _period(
            raw["Año"], raw["Periodo"], "BasePagina", offset, issues
        )
        metrics = _metrics(
            raw,
            {
                "planted_area_ha": "Área sembrada (ha)",
                "harvested_area_ha": "Área cosechada (ha)",
                "production_t": "Producción (t)",
                "reported_yield_t_ha": "Rendimiento (t/ha)",
            },
            "BasePagina",
            offset,
            issues,
        )
        crop_source_code = _digit_code(
            raw["Código del cultivo"],
            "Código del cultivo",
            "BasePagina",
            offset,
            issues,
        )
        shared_crop = {
            "crop_name": _text(raw["Cultivo"]),
            "cycle": _text(raw["Ciclo del cultivo"]),
            "group": _text(raw["Grupo cultivo"]),
            "subgroup": _text(raw["Subgrupo"]),
            "scientific_name": _text(raw["Nombre científico del cultivo"]),
            "physical_state": _text(raw["Estado físico del cultivo"]),
        }
        mapping = crop_mapping.get(_crop_mapping_key(shared_crop))
        if mapping is None:
            issues.append(
                ImportIssueData(
                    severity="ERROR",
                    code="MISSING_BASE_CROP_MAPPING",
                    sheet="BasePagina",
                    row=offset,
                    field="Código del cultivo",
                    message="No unambiguous BaseSIPRA crop mapping exists for the source row",
                )
            )

        if any(issue.severity == "ERROR" for issue in issues[row_issues_before:]):
            continue
        assert mapping is not None
        crop_base_code, general_classification = mapping
        crop_disaggregation = _text(raw["Desagregación cultivo"])
        variant_key = "␟".join(
            (
                crop_base_code,
                crop_source_code,
                crop_disaggregation,
                shared_crop["scientific_name"],
            )
        )
        values = {
            "source_row": offset,
            "department_code": department_code,
            "department_name": _text(raw["Departamento"]),
            "municipality_code": municipality_code,
            "municipality_name": _text(raw["Municipio"]),
            "crop_base_code": crop_base_code,
            "crop_source_code": crop_source_code,
            "crop_name": shared_crop["crop_name"],
            "crop_disaggregation": crop_disaggregation,
            "cycle": shared_crop["cycle"],
            "group": shared_crop["group"],
            "subgroup": shared_crop["subgroup"],
            "general_classification": general_classification,
            "year": year,
            "period_type": period_type.value,
            "period_label": _text(raw["Periodo"]).upper().replace(" ", ""),
            "chronological_order": _chronological_order(year, period_type),
            **metrics,
            "scientific_name": shared_crop["scientific_name"],
            "physical_state": shared_crop["physical_state"],
            "variant_key": variant_key,
        }
        if values["harvested_area_ha"] > values["planted_area_ha"]:
            issues.append(
                ImportIssueData(
                    severity="WARNING",
                    code="HARVESTED_EXCEEDS_PLANTED",
                    sheet="BasePagina",
                    row=offset,
                    field="Área cosechada (ha)",
                    message="Harvested area is greater than planted area",
                )
            )
        normalized.append(values)
    return normalized


def _period(
    year: object,
    label: object,
    sheet: str,
    row: int,
    issues: list[ImportIssueData],
) -> tuple[int, PeriodType]:
    try:
        return parse_period(year, str(label))  # type: ignore[arg-type]
    except _PeriodError as error:
        issues.append(
            ImportIssueData("ERROR", error.code, sheet, row, "Periodo", str(error))
        )
        return 0, PeriodType.ANNUAL


def _divipola(
    value: object,
    width: int,
    sheet: str,
    row: int,
    issues: list[ImportIssueData],
) -> str:
    code = _coerce_integral_text(value)
    if code is None or len(code) > width:
        issues.append(
            ImportIssueData(
                "ERROR",
                "INVALID_DIVIPOLA",
                sheet,
                row,
                "Código Dane",
                f"DIVIPOLA code must contain at most {width} digits: {value!r}",
            )
        )
        return ""
    return code.zfill(width)


def _validate_territorial_parent(
    department_code: str,
    municipality_code: str,
    sheet: str,
    row: int,
    issues: list[ImportIssueData],
) -> None:
    if department_code and municipality_code and not municipality_code.startswith(department_code):
        issues.append(
            ImportIssueData(
                "ERROR",
                "INVALID_DIVIPOLA",
                sheet,
                row,
                "Código Dane municipio",
                "Municipality code does not belong to the stated department",
            )
        )


def _digit_code(
    value: object,
    field: str,
    sheet: str,
    row: int,
    issues: list[ImportIssueData],
) -> str:
    code = _coerce_integral_text(value)
    if code is None:
        issues.append(
            ImportIssueData(
                "ERROR",
                "INVALID_CROP_CODE",
                sheet,
                row,
                field,
                f"Invalid code: {value!r}",
            )
        )
        return ""
    return code


def _coerce_integral_text(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else None
    text = _text(value)
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text if text.isdigit() else None


def _metrics(
    row_values: dict[str, Any],
    fields: dict[str, str],
    sheet: str,
    row: int,
    issues: list[ImportIssueData],
) -> dict[str, Decimal | None]:
    metrics: dict[str, Decimal | None] = {}
    for canonical, source_field in fields.items():
        allow_none = canonical == "reported_yield_t_ha"
        value = row_values[source_field]
        if value is None and allow_none:
            metrics[canonical] = None
            continue
        try:
            decimal_value = Decimal(str(value).strip().replace(",", "."))
        except (InvalidOperation, ValueError, AttributeError):
            issues.append(
                ImportIssueData(
                    "ERROR",
                    "INVALID_METRIC",
                    sheet,
                    row,
                    source_field,
                    f"Metric is not numeric: {value!r}",
                )
            )
            metrics[canonical] = None
            continue
        if decimal_value < 0:
            issues.append(
                ImportIssueData(
                    "ERROR",
                    "NEGATIVE_METRIC",
                    sheet,
                    row,
                    source_field,
                    f"Metric cannot be negative: {decimal_value}",
                )
            )
        metrics[canonical] = decimal_value
    return metrics


def _crop_mapping_key(values: dict[str, Any]) -> tuple[str, ...]:
    fields = (
        "crop_name",
        "cycle",
        "group",
        "subgroup",
        "scientific_name",
        "physical_state",
    )
    return tuple(
        _text(values[field]).casefold()
        for field in fields
    )


def _chronological_order(year: int, period_type: PeriodType) -> int:
    suffix_order = {
        PeriodType.ANNUAL: 0,
        PeriodType.SEMESTER_A: 1,
        PeriodType.SEMESTER_B: 2,
    }
    return year * 10 + suffix_order[period_type]


def _text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _frame(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame({column: [] for column in columns})
    return pl.DataFrame(
        rows,
        schema=list(columns),
        orient="row",
        strict=False,
        infer_schema_length=None,
    )


def _control_columns() -> tuple[str, ...]:
    page_only = {"crop_source_code", "crop_disaggregation", "variant_key"}
    return tuple(column for column in _RECORD_COLUMNS if column not in page_only)


def _dimensions(records: pl.DataFrame) -> dict[str, pl.DataFrame]:
    selections = {
        "departments": ("department_code", "department_name"),
        "municipalities": (
            "municipality_code",
            "municipality_name",
            "department_code",
        ),
        "crop_groups": ("group",),
        "crop_subgroups": ("group", "subgroup"),
        "crops": (
            "crop_base_code",
            "crop_name",
            "cycle",
            "group",
            "subgroup",
            "general_classification",
        ),
        "crop_variants": (
            "variant_key",
            "crop_base_code",
            "crop_source_code",
            "crop_disaggregation",
            "scientific_name",
        ),
        "physical_states": ("physical_state",),
        "periods": (
            "year",
            "period_type",
            "period_label",
            "chronological_order",
        ),
    }
    return {
        name: records.select(columns).unique(maintain_order=True)
        for name, columns in selections.items()
    }
