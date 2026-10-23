from enum import StrEnum

from pydantic import Field

from app.schemas.filters import AgricultureFilters


class RecordSortField(StrEnum):
    YEAR = "year"
    PERIOD_TYPE = "period_type"
    DEPARTMENT = "department"
    MUNICIPALITY = "municipality"
    CROP = "crop"
    CROP_VARIANT = "crop_variant"
    PHYSICAL_STATE = "physical_state"
    PLANTED_AREA = "planted_area_ha"
    HARVESTED_AREA = "harvested_area_ha"
    PRODUCTION = "production_t"
    REPORTED_YIELD = "reported_yield_t_ha"
    SOURCE_ROW = "source_row"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class RecordSelectionQuery(AgricultureFilters):
    search: str | None = None
    sort_by: RecordSortField = RecordSortField.YEAR
    sort_direction: SortDirection = SortDirection.DESC


class RecordPageQuery(RecordSelectionQuery):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
