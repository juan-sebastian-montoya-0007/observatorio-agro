from typing import Literal

from pydantic import Field
from sqlalchemy import Numeric, cast, func, select

from app.models import AgriculturalRecord, Crop, Department, Municipality, Period
from app.repositories.agriculture import AgricultureRepository
from app.schemas.filters import AgricultureFilters
from app.services.analytics import AnalyticsService


class AdvancedQuery(AgricultureFilters):
    dimension: Literal['municipality', 'department', 'crop', 'year'] = 'municipality'
    order_by: Literal['production_t', 'planted_area_ha', 'harvested_area_ha', 'yield_t_ha'] = 'production_t'
    direction: Literal['asc', 'desc'] = 'desc'
    limit: int = Field(default=20, ge=1, le=100)
    compare_year: int = Field(default=2024, ge=2019, le=2025)


def advanced_query(session, query: AdvancedQuery):
    filters = AgricultureFilters.model_validate(query.model_dump(include=set(AgricultureFilters.model_fields)))
    repo = AgricultureRepository(session)
    service = AnalyticsService(session)
    version = repo.latest_published_version()
    latest = filters.model_copy(update={'year_from': filters.year_to})
    envelope = service.summary(latest).model_dump(mode='json')
    dimensions = {
        'municipality': (Municipality.code, Municipality.name, Department.name),
        'department': (Department.code, Department.name),
        'crop': (Crop.id, Crop.name),
        'year': (Period.year,),
        'cycle': (Crop.cycle,),
    }

    def aggregate(selection, dimension):
        if version is None:
            return []
        keys = dimensions[dimension]
        planted = func.sum(AgriculturalRecord.planted_area_ha)
        harvested = func.sum(AgriculturalRecord.harvested_area_ha)
        production = func.sum(AgriculturalRecord.production_t)
        stmt = repo._with_joins(select(*keys, planted, harvested, production,
            cast(production / func.nullif(harvested, 0), Numeric(18, 4))))
        rows = session.execute(stmt.where(*repo._conditions(version.id, selection)).group_by(*keys)).all()
        return [dict(id=str(row[0]), name=str(row[1] if len(keys) > 1 else row[0]),
            department=str(row[2]) if dimension == 'municipality' else '',
            **dict(zip(['planted_area_ha', 'harvested_area_ha', 'production_t', 'yield_t_ha'],
                       [float(x) if x is not None else None for x in row[len(keys):]]))) for row in rows]

    current = aggregate(filters if query.dimension == 'year' else latest, query.dimension)
    previous = aggregate(filters.model_copy(update={'year_from': query.compare_year, 'year_to': query.compare_year}), query.dimension)
    baseline = {row['id']: row for row in previous}
    for row in current:
        before = baseline.get(row['id'], {}).get(query.indicator.value)
        now = row.get(query.indicator.value)
        row['variation'] = (now - before) / before * 100 if before and now is not None and query.dimension != 'year' else None
    valid = [row for row in current if row[query.order_by] is not None]
    valid.sort(key=lambda row: (row[query.order_by], row['name']), reverse=query.direction == 'desc')
    missing = [row for row in current if row[query.order_by] is None]
    municipalities = aggregate(latest, 'municipality')
    municipalities.sort(key=lambda row: row['yield_t_ha'] if row['yield_t_ha'] is not None else -1, reverse=True)
    national = filters.model_copy(update={'department_code': None, 'municipality_code': None})
    envelope['data'] = dict(rows=(valid + missing)[:query.limit], total=len(current),
        summary=envelope['data'], series=service.series(filters).model_dump(mode='json')['data'],
        national_series=service.series(national).model_dump(mode='json')['data'],
        national_summary=service.summary(national.model_copy(update={'year_from': filters.year_to})).model_dump(mode='json')['data'],
        municipalities=municipalities,
        top_yield=municipalities[:5], composition=aggregate(latest, 'cycle'),
        increases=sum(1 for row in current if (row['variation'] or 0) > 0),
        decreases=sum(1 for row in current if (row['variation'] or 0) < 0))
    return envelope
