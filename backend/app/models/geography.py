from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Department(Base):
    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    municipalities: Mapped[list[Municipality]] = relationship(back_populates="department")


class Municipality(Base):
    __tablename__ = "municipalities"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(5), unique=True)
    department_code: Mapped[str] = mapped_column(
        ForeignKey("departments.code", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    department: Mapped[Department] = relationship(back_populates="municipalities")


class TerritorialGeometry(Base):
    __tablename__ = "territorial_geometries"
    __table_args__ = (
        CheckConstraint("territorial_level IN ('DEPARTMENT', 'MUNICIPALITY')", name="level"),
        UniqueConstraint(
            "territorial_level", "divipola_code", "version", "is_simplified"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    territorial_level: Mapped[str] = mapped_column(String(20))
    divipola_code: Mapped[str] = mapped_column(String(5), index=True)
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True)
    )
    srid: Mapped[int] = mapped_column(Integer, default=4326, server_default="4326")
    version: Mapped[str] = mapped_column(String(100))
    is_simplified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    source_url: Mapped[str] = mapped_column(String(500))
    license: Mapped[str] = mapped_column(Text)
