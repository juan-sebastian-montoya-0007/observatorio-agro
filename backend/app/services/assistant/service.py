from urllib.parse import urlencode

from sqlalchemy import select

from app.models import Crop, Department, Municipality
from app.repositories.agriculture import AgricultureRepository
from app.schemas.assistant import AssistantResponse
from app.schemas.filters import AgricultureFilters
from app.services.analytics import AnalyticsService
from app.services.assistant.resolver import Clarification, resolve_name

LABELS = {
    "planted_area_ha": "área sembrada",
    "harvested_area_ha": "área cosechada",
    "production_t": "producción",
    "yield_t_ha": "rendimiento",
}


def format_number(value):
    if value is None:
        return "Sin datos"
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


class AssistantService:
    def __init__(self, session):
        self.session = session
        self.analytics = AnalyticsService(session)
        self.version = AgricultureRepository(session).latest_published_version()

    def catalog(self, context=None):
        catalog = {
            "crops": [dict(id=row.id, name=row.name) for row in self.session.scalars(select(Crop))],
            "departments": [
                dict(code=row.code, name=row.name)
                for row in self.session.scalars(select(Department))
            ],
        }
        if context and context.municipality_code:
            row = self.session.scalar(
                select(Municipality).where(Municipality.code == context.municipality_code)
            )
            if row:
                catalog["active_municipality"] = dict(code=row.code, name=row.name)
        return catalog

    def execute(self, action):
        if action.action == "out_of_scope":
            return AssistantResponse(
                status="out_of_scope",
                answer=(
                    "Puedo consultar áreas sembradas y cosechadas, producción y rendimiento "
                    "de los datos disponibles. No dispongo de precios, clima "
                    "ni áreas aún cosechables, "
                    "y no doy recomendaciones productivas."
                ),
            )
        if action.action == "clarify":
            return AssistantResponse(
                status="needs_clarification",
                answer=(
                    "Indica un cultivo, territorio, indicador y año entre 2019 y 2025. "
                    "Por ejemplo: ¿Qué departamento produjo más café en 2024?"
                ),
            )
        if not self.version:
            return AssistantResponse(
                status="no_data", answer="No hay una fuente publicada disponible."
            )
        try:
            return self._query(action)
        except Clarification as error:
            return AssistantResponse(status="needs_clarification", answer=str(error))

    def _query(self, action):
        year = (
            action.year_to
            or (action.year_from if action.action != "series" else None)
            or self.version.coverage_end_year
        )
        start = action.year_from or (2019 if action.action == "series" else year)
        if start > year or (action.action != "series" and start != year):
            raise Clarification(
                "Para un rango de años, pide una evolución histórica; "
                "para totales indica un solo año."
            )
        selection = dict(year_from=start, year_to=year, indicator=action.indicator)
        labels = []
        if action.crop:
            rows = [(row.id, row.name) for row in self.session.scalars(select(Crop))]
            code, name = resolve_name(action.crop, rows)
            selection["crop"] = code
            labels.append(name)
        if action.department:
            rows = [(row.code, row.name) for row in self.session.scalars(select(Department))]
            code, name = resolve_name(action.department, rows)
            selection["department"] = code
            labels.append(name)
        if action.municipality:
            stmt = select(Municipality)
            if "department" in selection:
                stmt = stmt.where(Municipality.department_code == selection["department"])
            rows = [(row.code, row.name) for row in self.session.scalars(stmt)]
            code, name = resolve_name(action.municipality, rows)
            selection.update(municipality=code, department=code[:2])
            labels.append(name)
        if action.period_type:
            selection.update(period_mode="SOURCE", period_type=action.period_type)
        filters = AgricultureFilters.model_validate(selection)
        if action.action == "rank":
            result = self.analytics.rankings(filters, dimension=action.dimension, limit=5)
            facts = [
                dict(label=r.name, value=str(r.value), unit=result.meta.unit) for r in result.data
            ]
        elif action.action == "series":
            result = self.analytics.series(filters)
            facts = [
                dict(
                    label=str(r.year),
                    value=str(getattr(r, action.indicator))
                    if getattr(r, action.indicator) is not None
                    else None,
                    unit=result.meta.unit,
                )
                for r in result.data
            ]
        else:
            result = self.analytics.summary(filters)
            facts = (
                [
                    dict(
                        label=LABELS[key],
                        value=str(getattr(result.data, key))
                        if getattr(result.data, key) is not None
                        else None,
                        unit="t/ha"
                        if key == "yield_t_ha"
                        else "t"
                        if key == "production_t"
                        else "ha",
                    )
                    for key in LABELS
                ]
                if result.data
                else []
            )
        applied = filters.model_dump(mode="json", by_alias=True, exclude_none=True)
        params = {k: v for k, v in applied.items() if k not in ("year_from", "year_to")}
        params["year"] = year
        context = " · ".join(labels) or "Todos los cultivos · Colombia"
        if not action.crop:
            context = "Todos los cultivos · " + context if labels else context
        if not action.department and not action.municipality and labels:
            context += " · Colombia"
        period = action.period_type or "Año agrícola"
        if not facts or not any(f["value"] is not None for f in facts):
            status, answer = (
                "no_data",
                f"No encontré datos para {context}, {start}–{year} ({period}).",
            )
        elif action.action == "rank":
            from decimal import Decimal

            first = facts[0]
            status = "answer"
            answer = (
                f"Primero en el ranking por {LABELS[action.indicator]}: {first['label']}, "
                f"{format_number(Decimal(first['value']))} {first['unit']}. "
                f"{context} · {year} · {period}. "
                "Se muestran hasta cinco resultados; puede haber empates."
            )
        else:
            status = "answer"
            title = (
                "Evolución de " + LABELS[action.indicator]
                if action.action == "series"
                else "Resumen"
            )
            answer = f"{title}: {context} · {start}–{year} · {period}."
        return AssistantResponse(
            status=status,
            answer=answer,
            facts=facts,
            applied_filters=applied,
            dashboard_url="/?" + urlencode(params),
            source_version=result.meta.source_version,
            warnings=[w.message for w in result.warnings],
        )
