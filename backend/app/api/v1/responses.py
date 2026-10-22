from app.models import SourceVersion
from app.schemas.common import AnalyticalResponse, CoverageEnvelope, ResponseMeta


def catalog_response(data, version: SourceVersion | None) -> AnalyticalResponse:
    return AnalyticalResponse(
        data=data,
        meta=ResponseMeta(
            source_version=version.version_label if version is not None else None,
            source_version_id=version.id if version is not None else None,
        ),
        coverage=CoverageEnvelope(
            status="AVAILABLE" if version is not None else "EMPTY",
            year_from=version.coverage_start_year if version is not None else None,
            year_to=version.coverage_end_year if version is not None else None,
        ),
        warnings=[],
        methodology=[],
    )
