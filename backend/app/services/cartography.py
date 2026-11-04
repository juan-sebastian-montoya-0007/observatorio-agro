"""Local official geometry joined to the same analytical policy as the dashboard."""

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.orm import Session

from app.models import AgriculturalRecord, Department, Municipality
from app.repositories.agriculture import AgricultureRepository
from app.schemas.filters import AgricultureFilters
from app.services.analytics import AnalyticsService
from app.statistics import Indicator

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "cartography"


@lru_cache(maxsize=3)
def _snapshot(file_name: str) -> dict:
    return json.loads((DATA_DIR / file_name).read_text(encoding="utf-8"))


class MapRepository(AgricultureRepository):
    def values(self, filters: AgricultureFilters, level: str, version_id: int) -> dict:
        code = Department.code if level == "department" else Municipality.code
        production = func.sum(AgriculturalRecord.production_t)
        harvested = func.sum(AgriculturalRecord.harvested_area_ha)
        metric = {
            Indicator.PLANTED_AREA: func.sum(AgriculturalRecord.planted_area_ha),
            Indicator.HARVESTED_AREA: harvested,
            Indicator.PRODUCTION: production,
            Indicator.YIELD: cast(production / func.nullif(harvested, 0), Numeric(18, 4)),
        }[filters.indicator]
        # Reuse the full filter and annual/semester policy; no ranking limit here.
        statement = (
            self._with_joins(select(
                code.label("code"), metric.label("value"),
                func.count(AgriculturalRecord.id).label("record_count"),
            ))
            .where(*self._conditions(version_id, filters))
            .group_by(code)
        )
        return {
            row.code: {
                "value": float(row.value) if row.value is not None else None,
                "record_count": int(row.record_count),
            }
            for row in self.session.execute(statement)
        }


def territorial_map(session: Session, filters: AgricultureFilters) -> dict:
    level = "municipality" if filters.department_code else "department"
    manifest = _snapshot("manifest.json")
    layer = manifest["layers"][level]
    collection = _snapshot(layer["file"])
    envelope = AnalyticsService(session).summary(filters).model_dump(mode="json")
    version_id = envelope["meta"]["source_version_id"]
    values = (
        MapRepository(session).values(filters, level, version_id)
        if version_id is not None else {}
    )
    features = []
    for feature in collection["features"]:
        properties = feature["properties"]
        if filters.department_code and properties["department_code"] != filters.department_code:
            continue
        features.append({
            "type": "Feature",
            "geometry": feature["geometry"],
            "properties": {
                **properties,
                **values.get(properties["code"], {"value": None, "record_count": 0}),
            },
        })
    geometry_codes = {feature["properties"]["code"] for feature in features}
    unmatched_codes = sorted(set(values) - geometry_codes)
    envelope["data"] = {
        "level": level,
        "geojson": {"type": "FeatureCollection", "features": features},
        "source": {
            "name": manifest["name"],
            "publisher": manifest["publisher"],
            "url": f"{manifest['source_url']}/{layer['layer']}",
            "retrieved_at": manifest["retrieved_at"],
            "sha256": layer["sha256"],
        },
        "unmatched_codes": unmatched_codes,
    }
    if unmatched_codes:
        envelope["warnings"].append({
            "code": "UNMAPPED_TERRITORIES",
            "message": f"{len(unmatched_codes)} territorios con datos no tienen geometría disponible.",
        })
    return envelope
