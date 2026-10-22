from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import polars as pl

from app.services.importer.normalizer import NormalizedWorkbook

_GRAIN = (
    "municipality_code",
    "crop_base_code",
    "cycle",
    "group",
    "subgroup",
    "year",
    "period_type",
    "scientific_name",
    "physical_state",
)
_ADDITIVE_METRICS = (
    "planted_area_ha",
    "harvested_area_ha",
    "production_t",
)


@dataclass(frozen=True, slots=True)
class ReconciliationMetric:
    name: str
    page_value: Decimal
    control_value: Decimal
    difference: Decimal
    key: str
    code: str = "RECONCILIATION_MISMATCH"


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    passed: bool
    page_rows: int
    control_rows: int
    mismatches: tuple[ReconciliationMetric, ...]


def reconcile_workbook(
    workbook: NormalizedWorkbook,
    tolerance: Decimal = Decimal("0.01"),
) -> ReconciliationReport:
    if tolerance < 0:
        raise ValueError("Reconciliation tolerance cannot be negative")

    page = _aggregate(workbook.records)
    control = _aggregate(workbook.control_rows)
    mismatches: list[ReconciliationMetric] = []

    keys = sorted(set(page) | set(control), key=lambda key: tuple(map(str, key)))
    for key in keys:
        readable_key = _readable_key(key)
        if key not in page or key not in control:
            page_presence = Decimal(key in page)
            control_presence = Decimal(key in control)
            mismatches.append(
                ReconciliationMetric(
                    name="row_presence",
                    page_value=page_presence,
                    control_value=control_presence,
                    difference=page_presence - control_presence,
                    key=readable_key,
                )
            )
            continue

        for metric in _ADDITIVE_METRICS:
            page_value = page[key][metric]
            control_value = control[key][metric]
            difference = page_value - control_value
            if abs(difference) > tolerance:
                mismatches.append(
                    ReconciliationMetric(
                        name=metric,
                        page_value=page_value,
                        control_value=control_value,
                        difference=difference,
                        key=readable_key,
                    )
                )

    return ReconciliationReport(
        passed=not mismatches,
        page_rows=len(page),
        control_rows=len(control),
        mismatches=tuple(mismatches),
    )


def _aggregate(frame: pl.DataFrame) -> dict[tuple[Any, ...], dict[str, Decimal]]:
    aggregated: dict[tuple[Any, ...], dict[str, Decimal]] = {}
    for row in frame.iter_rows(named=True):
        key = tuple(row[field] for field in _GRAIN)
        values = aggregated.setdefault(
            key,
            {metric: Decimal("0") for metric in _ADDITIVE_METRICS},
        )
        for metric in _ADDITIVE_METRICS:
            values[metric] += _decimal(row[metric])
    return aggregated


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _readable_key(key: tuple[Any, ...]) -> str:
    return ";".join(f"{field}={value}" for field, value in zip(_GRAIN, key, strict=True))
