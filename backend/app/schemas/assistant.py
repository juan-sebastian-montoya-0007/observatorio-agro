from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.filters import AgricultureFilters


class AssistantMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=500)
    history: list[AssistantMessage] = Field(default_factory=list, max_length=6)
    context: AgricultureFilters | None = None

    @field_validator("question")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Escribe una pregunta.")
        return value.strip()


class SelectedAction(BaseModel):
    """Only these parameters can reach read-only analytical services."""

    model_config = ConfigDict(extra="forbid")
    action: Literal["rank", "summary", "series", "clarify", "out_of_scope"]
    dimension: Literal["department", "municipality", "crop"] = "department"
    indicator: Literal["planted_area_ha", "harvested_area_ha", "production_t", "yield_t_ha"] = (
        "harvested_area_ha"
    )
    crop: str | None = Field(default=None, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    municipality: str | None = Field(default=None, max_length=150)
    year_from: int | None = Field(default=None, ge=2019, le=2025)
    year_to: int | None = Field(default=None, ge=2019, le=2025)
    period_type: Literal["ANNUAL", "SEMESTER_A", "SEMESTER_B"] | None = None


class AssistantResponse(BaseModel):
    status: Literal["answer", "no_data", "needs_clarification", "out_of_scope"]
    answer: str
    facts: list[dict[str, str | None]] = Field(default_factory=list)
    applied_filters: dict = Field(default_factory=dict)
    dashboard_url: str | None = None
    source: str = (
        "Datos obtenidos de las Evaluaciones Agropecuarias Municipales (EVA), "
        "publicadas por la UPRA."
    )
    source_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
