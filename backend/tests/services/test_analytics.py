from app.schemas.filters import AgricultureFilters
from app.services.analytics import AnalyticsService


def test_analytics_service_preserves_empty_coverage(session):
    response = AnalyticsService(session).summary(
        AgricultureFilters(department_code="08", year_from=2024, year_to=2024)
    )

    assert response.coverage.status == "EMPTY"
    assert response.data is None
