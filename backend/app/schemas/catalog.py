from pydantic import BaseModel


class CropVariantOut(BaseModel):
    id: int
    source_code: str
    disaggregation: str
    scientific_name: str


class CropOut(BaseModel):
    id: int
    base_code: str
    name: str
    cycle: str
    group: str
    subgroup: str
    general_classification: str
    variants: list[CropVariantOut]


class PeriodOut(BaseModel):
    year: int
    period_type: str
    label: str
    chronological_order: int


class YearCoverage(BaseModel):
    year_from: int
    year_to: int


class SourceOut(BaseModel):
    id: int
    name: str
    publisher: str
    version_label: str
    sha256: str
    coverage: YearCoverage
    status: str


class DepartmentOut(BaseModel):
    code: str
    name: str
    is_active: bool


class MunicipalityOut(BaseModel):
    code: str
    department_code: str
    name: str
    is_active: bool
