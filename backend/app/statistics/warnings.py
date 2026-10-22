from typing import TYPE_CHECKING

from app.statistics.types import AnalyticalWarning, Indicator

if TYPE_CHECKING:
    from app.schemas.filters import AgricultureFilters

_BREAK_INDICATORS = {
    Indicator.HARVESTED_AREA,
    Indicator.PRODUCTION,
    Indicator.YIELD,
}


def comparison_warnings(
    filters: "AgricultureFilters",
    *,
    latest_year: int,
) -> tuple[AnalyticalWarning, ...]:
    warnings: list[AnalyticalWarning] = []
    cycle_can_include_transients = filters.cycle is None or (
        "trans" in filters.cycle.casefold()
    )
    crosses_methodology_break = filters.year_from <= 2021 and filters.year_to >= 2022
    if (
        cycle_can_include_transients
        and filters.indicator in _BREAK_INDICATORS
        and crosses_methodology_break
    ):
        warnings.append(
            AnalyticalWarning(
                code="TRANSIENT_METHODOLOGY_BREAK_2021_2022",
                message=(
                    "Para cultivos transitorios cambió la referencia temporal de cosecha, "
                    "producción y rendimiento entre 2021 y 2022."
                ),
            )
        )

    if filters.year_to >= latest_year - 1 and filters.year_from <= latest_year:
        warnings.append(
            AnalyticalWarning(
                code="RECENT_DATA_PROVISIONAL",
                message="Las cifras de los dos años más recientes pueden recibir ajustes.",
            )
        )
    return tuple(warnings)
