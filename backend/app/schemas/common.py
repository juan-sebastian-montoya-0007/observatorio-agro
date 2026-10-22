from __future__ import annotations

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    source_version: str | None = None
    source_version_id: int | None = None
    indicator: str | None = None
    period_mode: str | None = None
    unit: str | None = None


class CoverageEnvelope(BaseModel):
    status: str
    year_from: int | None = None
    year_to: int | None = None
    record_count: int | None = None


class AnalyticalWarningOut(BaseModel):
    code: str
    message: str


class AnalyticalResponse[T](BaseModel):
    data: T
    meta: ResponseMeta
    coverage: CoverageEnvelope
    warnings: list[AnalyticalWarningOut] = Field(default_factory=list)
    methodology: list[str] = Field(default_factory=list)
