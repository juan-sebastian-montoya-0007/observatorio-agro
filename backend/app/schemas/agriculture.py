from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel

from app.models import PeriodType


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


class AgriculturalRecordOut(BaseModel):
    id: int
    department_code: str
    department_name: str
    municipality_code: str
    municipality_name: str
    year: int
    period_type: PeriodType
    crop_id: int
    crop_base_code: str
    crop_name: str
    crop_variant_id: int
    crop_variant_source_code: str
    crop_variant_disaggregation: str
    physical_state: str
    planted_area_ha: Decimal
    harvested_area_ha: Decimal
    production_t: Decimal
    reported_yield_t_ha: Decimal | None
    source_version_id: int
    source_version_label: str
    source_sheet: str | None
    source_row: int


class RecordPageOut(BaseModel):
    items: list[AgriculturalRecordOut]
    total: int
    page: int
    page_size: int
