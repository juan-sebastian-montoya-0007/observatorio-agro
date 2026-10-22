from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.models import PeriodType


class PeriodMode(StrEnum):
    SOURCE = "SOURCE"
    AGRICULTURAL_YEAR = "AGRICULTURAL_YEAR"


class Indicator(StrEnum):
    PLANTED_AREA = "planted_area_ha"
    HARVESTED_AREA = "harvested_area_ha"
    PRODUCTION = "production_t"
    YIELD = "yield_t_ha"


@dataclass(frozen=True, slots=True)
class AnalyticalWarning:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class Coverage:
    status: str
    available_period_types: frozenset[PeriodType]
    expected_period_types: frozenset[PeriodType]


@dataclass(frozen=True, slots=True)
class PeriodObservation:
    period_type: PeriodType
    planted_area_ha: Decimal
    harvested_area_ha: Decimal
    production_t: Decimal
    cycle: str


@dataclass(frozen=True, slots=True)
class PeriodSelection:
    planted_area_ha: Decimal
    harvested_area_ha: Decimal
    production_t: Decimal
    yield_t_ha: Decimal | None
    used_period_types: frozenset[PeriodType]
    excluded_period_types: frozenset[PeriodType]
    coverage: Coverage
    warnings: tuple[AnalyticalWarning, ...]
