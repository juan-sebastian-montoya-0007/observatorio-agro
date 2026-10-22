from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.responses import catalog_response
from app.db.session import get_session
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CropOut, PeriodOut, SourceOut
from app.schemas.common import AnalyticalResponse

router = APIRouter(prefix="/catalog", tags=["catalog"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/crops", response_model=AnalyticalResponse[list[CropOut]])
def crops(session: SessionDependency):
    repository = CatalogRepository(session)
    version = repository.latest_published_version()
    data = repository.crops(version.id) if version is not None else []
    return catalog_response(data, version)


@router.get("/periods", response_model=AnalyticalResponse[list[PeriodOut]])
def periods(session: SessionDependency):
    repository = CatalogRepository(session)
    version = repository.latest_published_version()
    data = repository.periods(version.id) if version is not None else []
    return catalog_response(data, version)


@router.get("/sources", response_model=AnalyticalResponse[list[SourceOut]])
def sources(session: SessionDependency):
    repository = CatalogRepository(session)
    version = repository.latest_published_version()
    return catalog_response(repository.sources(), version)
