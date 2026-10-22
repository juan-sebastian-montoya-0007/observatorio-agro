from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PeriodType(StrEnum):
    ANNUAL = "ANNUAL"
    SEMESTER_A = "SEMESTER_A"
    SEMESTER_B = "SEMESTER_B"


class CropGroup(Base):
    __tablename__ = "crop_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)

    subgroups: Mapped[list[CropSubgroup]] = relationship(back_populates="group")
    crops: Mapped[list[Crop]] = relationship(back_populates="group")


class CropSubgroup(Base):
    __tablename__ = "crop_subgroups"
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("crop_groups.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(150))

    group: Mapped[CropGroup] = relationship(back_populates="subgroups")
    crops: Mapped[list[Crop]] = relationship(back_populates="subgroup")


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    cycle: Mapped[str] = mapped_column(String(100))
    group_id: Mapped[int] = mapped_column(ForeignKey("crop_groups.id", ondelete="RESTRICT"))
    subgroup_id: Mapped[int] = mapped_column(
        ForeignKey("crop_subgroups.id", ondelete="RESTRICT")
    )
    general_classification: Mapped[str] = mapped_column(String(150))

    group: Mapped[CropGroup] = relationship(back_populates="crops")
    subgroup: Mapped[CropSubgroup] = relationship(back_populates="crops")
    variants: Mapped[list[CropVariant]] = relationship(
        back_populates="crop", cascade="all, delete-orphan"
    )


class CropVariant(Base):
    __tablename__ = "crop_variants"
    __table_args__ = (
        UniqueConstraint("crop_id", "source_code", "disaggregation", "scientific_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id", ondelete="RESTRICT"))
    source_code: Mapped[str] = mapped_column(String(30))
    disaggregation: Mapped[str] = mapped_column(String(250))
    scientific_name: Mapped[str] = mapped_column(String(250), default="", server_default="")

    crop: Mapped[Crop] = relationship(back_populates="variants")


class PhysicalState(Base):
    __tablename__ = "physical_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)


class Period(Base):
    __tablename__ = "periods"
    __table_args__ = (UniqueConstraint("year", "period_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    period_type: Mapped[PeriodType] = mapped_column(
        Enum(PeriodType, name="period_type", native_enum=True)
    )
    original_label: Mapped[str] = mapped_column(String(20))
    chronological_order: Mapped[int] = mapped_column(Integer, index=True)


class AgriculturalRecord(Base):
    __tablename__ = "agricultural_records"
    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "municipality_id",
            "crop_variant_id",
            "period_id",
            "physical_state_id",
            name="uq_agricultural_record_fact_key",
        ),
        Index(
            "ix_agricultural_records_version_period_territory_crop",
            "source_version_id",
            "period_id",
            "municipality_id",
            "crop_variant_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_version_id: Mapped[int] = mapped_column(
        ForeignKey("source_versions.id", ondelete="CASCADE")
    )
    municipality_id: Mapped[int] = mapped_column(
        ForeignKey("municipalities.id", ondelete="RESTRICT")
    )
    crop_variant_id: Mapped[int] = mapped_column(
        ForeignKey("crop_variants.id", ondelete="RESTRICT")
    )
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id", ondelete="RESTRICT"))
    physical_state_id: Mapped[int] = mapped_column(
        ForeignKey("physical_states.id", ondelete="RESTRICT")
    )
    planted_area_ha: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    harvested_area_ha: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    production_t: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    reported_yield_t_ha: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    source_row: Mapped[int] = mapped_column(Integer)
    trace_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, server_default="{}")
