from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class RankingDimension(StrEnum):
    DEPARTMENT = "department"
    MUNICIPALITY = "municipality"
    CROP = "crop"


class SummaryData(BaseModel):
    planted_area_ha: Decimal
    harvested_area_ha: Decimal
    production_t: Decimal
    yield_t_ha: Decimal | None
    record_count: int


class SeriesPointOut(BaseModel):
    year: int
    period_type: str
    planted_area_ha: Decimal
    harvested_area_ha: Decimal
    production_t: Decimal
    yield_t_ha: Decimal | None
    record_count: int


class RankingItemOut(BaseModel):
    rank: int
    id: str | int
    name: str
    value: Decimal
    record_count: int
