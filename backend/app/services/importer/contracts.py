from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True, slots=True)
class WorkbookFingerprint:
    sha256: str
    file_name: str


@dataclass(frozen=True, slots=True)
class ParsedWorkbook:
    page: pl.DataFrame
    control: pl.DataFrame
    notes: tuple[str, ...]


class WorkbookContractError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        sheet: str | None = None,
        row: int | None = None,
        field: str | None = None,
    ) -> None:
        self.code = code
        self.sheet = sheet
        self.row = row
        self.field = field

        location = ", ".join(
            part
            for part in (
                f"sheet={sheet}" if sheet is not None else "",
                f"row={row}" if row is not None else "",
                f"field={field}" if field is not None else "",
            )
            if part
        )
        detail = f" ({location})" if location else ""
        super().__init__(f"{code}{detail}: {message}")
