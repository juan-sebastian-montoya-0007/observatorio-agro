from decimal import Decimal

import polars as pl

from app.services.importer.normalizer import NormalizedWorkbook
from app.services.importer.reconciliation import reconcile_workbook

SHARED = {
    "source_row": 10,
    "department_code": "05",
    "department_name": "ANTIOQUIA",
    "municipality_code": "05001",
    "municipality_name": "MEDELLÍN",
    "crop_base_code": "10807",
    "crop_source_code": "1080701",
    "crop_name": "PAPA",
    "crop_disaggregation": "PAPA CRIOLLA",
    "cycle": "TRANSITORIO",
    "group": "ALIMENTARIOS",
    "subgroup": "TUBÉRCULOS",
    "general_classification": "ALIMENTARIOS",
    "year": 2025,
    "period_type": "ANNUAL",
    "period_label": "2025",
    "chronological_order": 20250,
    "planted_area_ha": Decimal("4"),
    "harvested_area_ha": Decimal("3"),
    "production_t": Decimal("6"),
    "reported_yield_t_ha": Decimal("2"),
    "scientific_name": "Solanum tuberosum",
    "physical_state": "EN FRESCO",
    "variant_key": "10807␟1080701␟PAPA CRIOLLA␟Solanum tuberosum",
}


def _normalized(records: list[dict], control_rows: list[dict]) -> NormalizedWorkbook:
    return NormalizedWorkbook(
        records=pl.DataFrame(records, strict=False, infer_schema_length=None),
        control_rows=pl.DataFrame(control_rows, strict=False, infer_schema_length=None),
        dimensions={},
        issues=(),
    )


def _control(**overrides) -> dict:
    page_only = {"crop_source_code", "crop_disaggregation", "variant_key"}
    return {key: value for key, value in (SHARED | overrides).items() if key not in page_only}


def test_reconciliation_collapses_variants_to_control_grain():
    second_variant = SHARED | {
        "source_row": 11,
        "crop_source_code": "1080702",
        "crop_disaggregation": "PAPA CAPIRA",
        "variant_key": "10807␟1080702␟PAPA CAPIRA␟Solanum tuberosum",
        "planted_area_ha": Decimal("6"),
        "harvested_area_ha": Decimal("5"),
        "production_t": Decimal("10"),
    }
    control = _control(
        planted_area_ha=Decimal("10"),
        harvested_area_ha=Decimal("8"),
        production_t=Decimal("16"),
    )

    report = reconcile_workbook(_normalized([SHARED, second_variant], [control]))

    assert report.passed is True
    assert report.page_rows == 1
    assert report.control_rows == 1
    assert report.mismatches == ()


def test_reconciliation_keeps_annual_and_semesters_separate():
    records = []
    controls = []
    for period_type, label, order in (
        ("ANNUAL", "2025", 20250),
        ("SEMESTER_A", "2025A", 20251),
        ("SEMESTER_B", "2025B", 20252),
    ):
        row = SHARED | {
            "period_type": period_type,
            "period_label": label,
            "chronological_order": order,
        }
        records.append(row)
        controls.append(_control(**row))

    report = reconcile_workbook(_normalized(records, controls))

    assert report.passed is True
    assert report.page_rows == 3
    assert report.control_rows == 3


def test_reconciliation_reports_exact_metric_difference_with_readable_key():
    control = _control(production_t=Decimal("5.25"))

    report = reconcile_workbook(_normalized([SHARED], [control]))

    assert report.passed is False
    mismatch = next(item for item in report.mismatches if item.name == "production_t")
    assert mismatch.code == "RECONCILIATION_MISMATCH"
    assert mismatch.page_value == Decimal("6")
    assert mismatch.control_value == Decimal("5.25")
    assert mismatch.difference == Decimal("0.75")
    assert "municipality_code=05001" in mismatch.key
    assert "period_type=ANNUAL" in mismatch.key
