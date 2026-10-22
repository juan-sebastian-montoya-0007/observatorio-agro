from decimal import Decimal

import polars as pl
import pytest

from app.models import PeriodType
from app.services.importer.contracts import ParsedWorkbook
from app.services.importer.normalizer import (
    NormalizationError,
    normalize_workbook,
    parse_period,
)
from app.services.importer.source_contract import BASE_PAGINA_HEADERS, BASE_SIPRA_HEADERS

PAGE_BASE = {
    "Código Dane departamento": 5,
    "Departamento": "  ANTIOQUIA  ",
    "Código Dane municipio": 5001,
    "Municipio": " MEDELLÍN ",
    "Desagregación cultivo": " PAPA CRIOLLA ",
    "Cultivo": " PAPA ",
    "Ciclo del cultivo": " TRANSITORIO ",
    "Grupo cultivo": " ALIMENTARIOS ",
    "Subgrupo": " TUBÉRCULOS ",
    "Año": 2025,
    "Periodo": "2025A",
    "Área sembrada (ha)": 0,
    "Área cosechada (ha)": 0,
    "Producción (t)": 0,
    "Rendimiento (t/ha)": 0,
    "Nombre científico del cultivo": " Solanum phureja ",
    "Código del cultivo": 1080701,
    "Estado físico del cultivo": " EN FRESCO ",
}

CONTROL_BASE = {
    "codigoDepartamento": 5,
    "departamento": "ANTIOQUIA",
    "codigoMunicipio": 5001,
    "municipio": "MEDELLÍN",
    "especie": "PAPA",
    "nombre_tipo_ciclo": "TRANSITORIO",
    "grupo_especie": "ALIMENTARIOS",
    "subGrupo_Especie": "TUBÉRCULOS",
    "anho": 2025,
    "Periodo": "2025A",
    "AreaSembrada": 0,
    "AreaCosechada": 0,
    "produccio": 0,
    "rendimiento": 0,
    "cod_cultiv": 10807,
    "nombre_cientifico": "Solanum phureja",
    "EstadoFisicoProduccio": "EN FRESCO",
    "Clasifica_grupo": "ALIMENTARIOS",
}


def _row(base: dict[str, object], **overrides: object) -> tuple[object, ...]:
    values = base | overrides
    headers = BASE_PAGINA_HEADERS if "Cultivo" in base else BASE_SIPRA_HEADERS
    return tuple(values[header] for header in headers)


def _parsed(
    *,
    page_rows: list[tuple[object, ...]] | None = None,
    control_rows: list[tuple[object, ...]] | None = None,
) -> ParsedWorkbook:
    return ParsedWorkbook(
        page=pl.DataFrame(
            page_rows or [_row(PAGE_BASE)],
            schema=list(BASE_PAGINA_HEADERS),
            orient="row",
            strict=False,
        ),
        control=pl.DataFrame(
            control_rows or [_row(CONTROL_BASE)],
            schema=list(BASE_SIPRA_HEADERS),
            orient="row",
            strict=False,
        ),
        notes=("Fuente: EVA -UPRA",),
    )


def test_codes_keep_required_width_and_zero_is_not_missing():
    normalized = normalize_workbook(_parsed())

    row = normalized.records.row(0, named=True)
    assert row["department_code"] == "05"
    assert row["municipality_code"] == "05001"
    assert row["planted_area_ha"] == Decimal("0")
    assert normalized.issues == ()


def test_variant_identity_keeps_scientific_name_and_physical_state():
    second_page = _row(
        PAGE_BASE,
        **{
            "Desagregación cultivo": "PAPA CAPIRA",
            "Nombre científico del cultivo": "Solanum tuberosum",
            "Código del cultivo": 1080702,
            "Área sembrada (ha)": 20,
            "Área cosechada (ha)": 18,
            "Producción (t)": 36,
            "Rendimiento (t/ha)": 2,
        },
    )
    second_control = _row(
        CONTROL_BASE,
        **{
            "nombre_cientifico": "Solanum tuberosum",
            "AreaSembrada": 20,
            "AreaCosechada": 18,
            "produccio": 36,
            "rendimiento": 2,
        },
    )

    normalized = normalize_workbook(
        _parsed(
            page_rows=[_row(PAGE_BASE), second_page],
            control_rows=[_row(CONTROL_BASE), second_control],
        )
    )

    assert normalized.records.select("variant_key").n_unique() == 2
    assert normalized.records.get_column("physical_state").to_list() == [
        "EN FRESCO",
        "EN FRESCO",
    ]
    assert normalized.dimensions["crops"].row(0, named=True)["general_classification"] == (
        "ALIMENTARIOS"
    )


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("2025", PeriodType.ANNUAL),
        ("2025A", PeriodType.SEMESTER_A),
        ("2025B", PeriodType.SEMESTER_B),
    ],
)
def test_parse_period_keeps_annual_and_semesters_distinct(label, expected):
    assert parse_period(2025, label) == (2025, expected)


@pytest.mark.parametrize(
    ("parsed", "expected_code"),
    [
        (
            _parsed(
                page_rows=[_row(PAGE_BASE, **{"Producción (t)": -1})],
            ),
            "NEGATIVE_METRIC",
        ),
        (
            _parsed(
                page_rows=[_row(PAGE_BASE, **{"Periodo": "2024B"})],
            ),
            "PERIOD_MISMATCH",
        ),
        (
            _parsed(
                page_rows=[_row(PAGE_BASE, **{"Código Dane municipio": "5X001"})],
            ),
            "INVALID_DIVIPOLA",
        ),
        (
            _parsed(
                control_rows=[
                    _row(CONTROL_BASE),
                    _row(CONTROL_BASE, **{"cod_cultiv": 99999}),
                ]
            ),
            "AMBIGUOUS_BASE_CROP",
        ),
    ],
)
def test_structural_data_errors_are_fatal(parsed, expected_code):
    with pytest.raises(NormalizationError) as error:
        normalize_workbook(parsed)

    assert expected_code in {issue.code for issue in error.value.issues}


def test_harvested_above_planted_is_warning_and_record_is_kept():
    parsed = _parsed(
        page_rows=[
            _row(
                PAGE_BASE,
                **{
                    "Área sembrada (ha)": 4,
                    "Área cosechada (ha)": 5,
                    "Producción (t)": 10,
                    "Rendimiento (t/ha)": 2,
                },
            )
        ],
        control_rows=[
            _row(
                CONTROL_BASE,
                **{
                    "AreaSembrada": 4,
                    "AreaCosechada": 5,
                    "produccio": 10,
                    "rendimiento": 2,
                },
            )
        ],
    )

    normalized = normalize_workbook(parsed)

    assert normalized.records.height == 1
    assert [(issue.severity, issue.code) for issue in normalized.issues] == [
        ("WARNING", "HARVESTED_EXCEEDS_PLANTED")
    ]
