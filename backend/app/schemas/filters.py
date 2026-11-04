from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import PeriodType
from app.statistics.types import Indicator, PeriodMode

DepartmentCode = Annotated[str, StringConstraints(pattern=r"^\d{2}$")]
MunicipalityCode = Annotated[str, StringConstraints(pattern=r"^\d{5}$")]


class AgricultureFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    department_code: DepartmentCode | None = Field(default=None, alias="department")
    municipality_code: MunicipalityCode | None = Field(default=None, alias="municipality")
    crop_id: int | None = Field(default=None, gt=0, alias="crop")
    crop_variant_id: int | None = Field(default=None, gt=0, alias="crop_variant")
    group: str | None = None
    subgroup: str | None = None
    cycle: str | None = None
    classification: str | None = None
    physical_state: str | None = None
    year_from: int = Field(default=2019, ge=2019, le=2025)
    year_to: int = Field(default=2025, ge=2019, le=2025)
    period_mode: PeriodMode = PeriodMode.AGRICULTURAL_YEAR
    period_type: PeriodType | None = Field(default=None, alias="period_type")
    indicator: Indicator = Indicator.PRODUCTION

    @model_validator(mode="after")
    def validate_dependencies(self) -> Self:
        if self.period_mode is PeriodMode.SOURCE and self.period_type is None:
            raise ValueError("MISSING_SOURCE_PERIOD: SOURCE requires period_type")
        if self.period_mode is PeriodMode.AGRICULTURAL_YEAR and self.period_type is not None:
            raise ValueError("INVALID_SOURCE_PERIOD: AGRICULTURAL_YEAR forbids period_type")
        if self.year_from > self.year_to:
            raise ValueError("INVALID_YEAR_RANGE: year_from must not exceed year_to")
        if self.municipality_code is not None and self.department_code is None:
            raise ValueError(
                "MISSING_PARENT_FILTER: municipality requires a department filter"
            )
        if (
            self.municipality_code is not None
            and self.department_code is not None
            and not self.municipality_code.startswith(self.department_code)
        ):
            raise ValueError(
                "INVALID_TERRITORIAL_RELATION: municipality does not belong to department"
            )
        return self
