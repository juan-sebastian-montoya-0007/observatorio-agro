from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models import (
    AgriculturalRecord,
    Crop,
    CropVariant,
    Department,
    Municipality,
    Period,
    Source,
    SourceVersion,
)


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def latest_published_version(self) -> SourceVersion | None:
        return self.session.scalar(
            select(SourceVersion)
            .where(SourceVersion.status == "PUBLISHED")
            .order_by(SourceVersion.coverage_end_year.desc(), SourceVersion.id.desc())
            .limit(1)
        )

    def crops(self, source_version_id: int) -> list[dict[str, object]]:
        rows = self.session.execute(
            select(Crop, CropVariant)
            .join(CropVariant, CropVariant.crop_id == Crop.id)
            .where(
                exists(
                    select(1).where(
                        AgriculturalRecord.crop_variant_id == CropVariant.id,
                        AgriculturalRecord.source_version_id == source_version_id,
                    )
                )
            )
            .order_by(
                func.lower(Crop.name),
                func.lower(CropVariant.disaggregation),
                CropVariant.source_code,
            )
        ).all()
        crops: dict[int, dict[str, object]] = {}
        for crop, variant in rows:
            item = crops.setdefault(
                crop.id,
                {
                    "id": crop.id,
                    "base_code": crop.base_code,
                    "name": crop.name,
                    "cycle": crop.cycle,
                    "group": crop.group.name,
                    "subgroup": crop.subgroup.name,
                    "general_classification": crop.general_classification,
                    "variants": [],
                },
            )
            variants = item["variants"]
            assert isinstance(variants, list)
            variants.append(
                {
                    "id": variant.id,
                    "source_code": variant.source_code,
                    "disaggregation": variant.disaggregation,
                    "scientific_name": variant.scientific_name,
                }
            )
        return list(crops.values())

    def periods(self, source_version_id: int) -> list[dict[str, object]]:
        periods = self.session.scalars(
            select(Period)
            .join(AgriculturalRecord, AgriculturalRecord.period_id == Period.id)
            .where(AgriculturalRecord.source_version_id == source_version_id)
            .distinct()
            .order_by(Period.chronological_order)
        ).all()
        return [
            {
                "year": period.year,
                "period_type": period.period_type.value,
                "label": period.original_label,
                "chronological_order": period.chronological_order,
            }
            for period in periods
        ]

    def sources(self) -> list[dict[str, object]]:
        rows = self.session.execute(
            select(SourceVersion, Source)
            .join(Source, Source.id == SourceVersion.source_id)
            .where(SourceVersion.status == "PUBLISHED")
            .order_by(SourceVersion.coverage_end_year.desc(), SourceVersion.id.desc())
        ).all()
        return [
            {
                "id": version.id,
                "name": source.name,
                "publisher": source.publisher,
                "version_label": version.version_label,
                "sha256": version.sha256,
                "coverage": {
                    "year_from": version.coverage_start_year,
                    "year_to": version.coverage_end_year,
                },
                "status": version.status,
            }
            for version, source in rows
        ]

    def departments(self, source_version_id: int) -> list[dict[str, object]]:
        departments = self.session.scalars(
            select(Department)
            .where(
                exists(
                    select(1)
                    .select_from(Municipality)
                    .join(
                        AgriculturalRecord,
                        AgriculturalRecord.municipality_id == Municipality.id,
                    )
                    .where(
                        Municipality.department_code == Department.code,
                        AgriculturalRecord.source_version_id == source_version_id,
                    )
                )
            )
            .order_by(func.lower(Department.name), Department.code)
        ).all()
        return [
            {
                "code": department.code,
                "name": department.name,
                "is_active": department.is_active,
            }
            for department in departments
        ]

    def municipalities(
        self,
        source_version_id: int,
        department_code: str,
    ) -> list[dict[str, object]]:
        municipalities = self.session.scalars(
            select(Municipality)
            .where(
                Municipality.department_code == department_code,
                exists(
                    select(1).where(
                        AgriculturalRecord.municipality_id == Municipality.id,
                        AgriculturalRecord.source_version_id == source_version_id,
                    )
                ),
            )
            .order_by(func.lower(Municipality.name), Municipality.code)
        ).all()
        return [
            {
                "code": municipality.code,
                "department_code": municipality.department_code,
                "name": municipality.name,
                "is_active": municipality.is_active,
            }
            for municipality in municipalities
        ]
