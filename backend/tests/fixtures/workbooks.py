from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.importer.source_contract import BASE_PAGINA_HEADERS, BASE_SIPRA_HEADERS

PAGE_ROWS = (
    (
        "05",
        "ANTIOQUIA",
        "05001",
        "MEDELLÍN",
        "PAPA CRIOLLA",
        "PAPA",
        "TRANSITORIO",
        "ALIMENTARIOS",
        "TUBÉRCULOS",
        2025,
        "2025A",
        10,
        9,
        18,
        2,
        "Solanum phureja",
        "1080701",
        "EN FRESCO",
    ),
    (
        "05",
        "ANTIOQUIA",
        "05001",
        "MEDELLÍN",
        "PAPA CAPIRA",
        "PAPA",
        "TRANSITORIO",
        "ALIMENTARIOS",
        "TUBÉRCULOS",
        2025,
        "2025A",
        20,
        18,
        36,
        2,
        "Solanum tuberosum",
        "1080702",
        "EN FRESCO",
    ),
)

CONTROL_ROW = (
    "05",
    "ANTIOQUIA",
    "05001",
    "MEDELLÍN",
    "PAPA",
    "TRANSITORIO",
    "ALIMENTARIOS",
    "TUBÉRCULOS",
    2025,
    "2025A",
    30,
    27,
    54,
    2,
    "10807",
    "Solanum spp.",
    "EN FRESCO",
    "ALIMENTARIOS",
)


def _save_workbook(
    path: Path,
    *,
    page_headers: tuple[str, ...] = BASE_PAGINA_HEADERS,
    include_control: bool = True,
) -> Path:
    workbook = Workbook()
    page = workbook.active
    page.title = "BasePagina"
    page.append([None] * len(page_headers))
    page.append(["EVALUACIONES AGROPECUARIAS MUNICIPALES"])
    page.append(["BASE AGRÍCOLA 2019 - 2025"])
    page.append(["Fuente: EVA -UPRA, con base en información municipal"])
    page.append(["* Las cifras de los dos últimos años son susceptibles de modificación."])
    page.append([None] * len(page_headers))
    page.append([None] * len(page_headers))
    page.append([None] * len(page_headers))
    page.append(page_headers)
    for row in PAGE_ROWS:
        page.append(row)

    if include_control:
        control = workbook.create_sheet("BaseSIPRA")
        control.append(BASE_SIPRA_HEADERS)
        control.append(CONTROL_ROW)

    workbook.save(path)
    workbook.close()
    return path


@pytest.fixture
def valid_workbook(tmp_path: Path) -> Path:
    return _save_workbook(tmp_path / "valid.xlsx")


@pytest.fixture
def workbook_with_changed_header(tmp_path: Path) -> Path:
    headers = list(BASE_PAGINA_HEADERS)
    headers[11] = "Área sembrada"
    return _save_workbook(tmp_path / "changed-header.xlsx", page_headers=tuple(headers))


@pytest.fixture
def workbook_without_control_sheet(tmp_path: Path) -> Path:
    return _save_workbook(tmp_path / "missing-sheet.xlsx", include_control=False)
