import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.responses import catalog_response
from app.db.session import get_session
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import DepartmentOut, MunicipalityOut
from app.schemas.common import AnalyticalResponse

router = APIRouter(prefix="/geography", tags=["geography"])
SessionDependency = Annotated[Session, Depends(get_session)]
DepartmentCodeQuery = Annotated[str, Query()]


@router.get("/departments", response_model=AnalyticalResponse[list[DepartmentOut]])
def departments(session: SessionDependency):
    repository = CatalogRepository(session)
    version = repository.latest_published_version()
    data = repository.departments(version.id) if version is not None else []
    return catalog_response(data, version)


@router.get(
    "/municipalities",
    response_model=AnalyticalResponse[list[MunicipalityOut]],
)
def municipalities(
    department_code: DepartmentCodeQuery,
    session: SessionDependency,
):
    if re.fullmatch(r"\d{2}", department_code) is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_DEPARTMENT_CODE",
                "message": "department_code must contain exactly two digits",
            },
        )
    repository = CatalogRepository(session)
    version = repository.latest_published_version()
    data = (
        repository.municipalities(version.id, department_code)
        if version is not None
        else []
    )
    return catalog_response(data, version)
