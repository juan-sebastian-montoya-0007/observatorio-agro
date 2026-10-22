from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.agriculture import RankingDimension, RankingItemOut, SeriesPointOut, SummaryData
from app.schemas.common import AnalyticalResponse
from app.schemas.filters import AgricultureFilters
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/agriculture", tags=["agriculture"])
SessionDependency = Annotated[Session, Depends(get_session)]
FilterQuery = Annotated[AgricultureFilters, Query()]


@router.get("/summary", response_model=AnalyticalResponse[SummaryData | None])
def summary(filters: FilterQuery, session: SessionDependency):
    return AnalyticsService(session).summary(filters)


@router.get("/series", response_model=AnalyticalResponse[list[SeriesPointOut]])
def series(filters: FilterQuery, session: SessionDependency):
    return AnalyticsService(session).series(filters)


@router.get("/rankings", response_model=AnalyticalResponse[list[RankingItemOut]])
def rankings(
    filters: FilterQuery,
    session: SessionDependency,
    dimension: Annotated[RankingDimension, Query()],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    if dimension is RankingDimension.MUNICIPALITY and filters.department_code is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MISSING_PARENT_FILTER",
                "message": "municipality ranking requires a department filter",
            },
        )
    return AnalyticsService(session).rankings(
        filters,
        dimension=dimension.value,
        limit=limit,
    )
