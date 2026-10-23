from collections.abc import Iterable
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.db.session import get_session
from app.repositories.agriculture import AgricultureRepository
from app.schemas.records import RecordSelectionQuery
from app.services.exports import AgricultureExportService, ExportRowLimitExceeded

router = APIRouter(prefix="/exports", tags=["exports"])
SessionDependency = Annotated[Session, Depends(get_session)]


class ExportFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"


class ClosingStreamingResponse(StreamingResponse):
    def __init__(self, content: Iterable[str | bytes], **kwargs) -> None:
        self.closeable_content = content
        super().__init__(content, **kwargs)

    async def stream_response(self, send) -> None:
        try:
            await super().stream_response(send)
        finally:
            close = getattr(self.closeable_content, "close", None)
            if close is not None:
                close()


@router.get("/agriculture")
def export_agriculture(
    request: Request,
    selection: Annotated[RecordSelectionQuery, Query()],
    session: SessionDependency,
    format: Annotated[ExportFormat, Query()],
):
    settings = request.app.state.settings
    repository = AgricultureRepository(session)
    version = repository.latest_published_version()
    service = AgricultureExportService(
        repository,
        source_version_id=version.id if version is not None else None,
        max_rows=settings.export_max_rows,
        batch_size=settings.export_batch_size,
    )
    try:
        service.ensure_within_limit(selection)
    except ExportRowLimitExceeded as error:
        raise HTTPException(
            status_code=413,
            detail={
                "code": error.code,
                "message": "La exportación supera el límite de filas permitido.",
                "row_count": error.row_count,
                "max_rows": error.max_rows,
            },
        ) from error

    if format is ExportFormat.CSV:
        filename = "agriculture-records.csv"
        content = service.stream_csv(selection)
        media_type = "text/csv"
    else:
        filename = "agriculture-records.xlsx"
        path = service.build_xlsx(selection)
        content = service.stream_xlsx(path)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return ClosingStreamingResponse(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
