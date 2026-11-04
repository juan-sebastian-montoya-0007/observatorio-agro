from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.agriculture import (
    RankingDimension,
    RankingItemOut,
    RecordPageOut,
    SeriesPointOut,
    SummaryData,
)
from app.schemas.common import AnalyticalResponse
from app.schemas.filters import AgricultureFilters
from app.schemas.records import RecordPageQuery
from app.services.analytics import AnalyticsService
from app.services.advanced import AdvancedQuery, advanced_query

router = APIRouter(prefix="/agriculture", tags=["agriculture"])
SessionDependency = Annotated[Session, Depends(get_session)]
FilterQuery = Annotated[AgricultureFilters, Query()]


@router.get('/advanced')
def advanced(query: Annotated[AdvancedQuery, Query()], session: SessionDependency):
    return advanced_query(session, query)


@router.get("/records", response_model=AnalyticalResponse[RecordPageOut])
def records(query: Annotated[RecordPageQuery, Query()], session: SessionDependency):
    return AnalyticsService(session).records(query)


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
    return AnalyticsService(session).rankings(
        filters,
        dimension=dimension.value,
        limit=limit,
    )
