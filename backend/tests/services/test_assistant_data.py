from app.schemas.assistant import SelectedAction
from app.services.assistant.service import AssistantService


def test_real_aggregates_rendered_without_model_numbers(session, fact_factory):
    session.add(fact_factory())
    session.commit()
    service = AssistantService(session)
    result = service.execute(SelectedAction(action='rank', crop='papa', year_to=2024))
    assert result.status == 'answer'
    assert result.facts[0]['label'] == 'ANTIOQUIA'
    assert float(result.facts[0]['value']) == 9
    assert result.facts[0]['unit'] == 'ha'
    assert '9,00 ha' in result.answer
    assert 'year=2024' in result.dashboard_url
    assert 'UPRA' in result.source
    summary = service.execute(SelectedAction(action='summary', crop='papa', year_to=2024))
    assert float(summary.facts[-1]['value']) == 2
    series = service.execute(SelectedAction(action='series', crop='papa', year_from=2024, year_to=2024))
    assert series.facts[0]['label'] == '2024'
    assert float(series.facts[0]['value']) == 9
    empty = service.execute(SelectedAction(action='summary', year_to=2025))
    assert empty.status == 'no_data'
    unknown = service.execute(SelectedAction(action='rank', crop='inexistente'))
    assert unknown.status == 'needs_clarification'
    rejected = service.execute(SelectedAction(action='out_of_scope'))
    assert rejected.facts == []
    assert rejected.status == 'out_of_scope'


def test_single_start_year_and_active_municipality_catalog(session, fact_factory):
    session.add(fact_factory())
    session.commit()
    service = AssistantService(session)
    response = service.execute(SelectedAction(action='summary', year_from=2024))
    assert response.status == 'answer'
    assert response.applied_filters['year_to'] == 2024
    from app.schemas.filters import AgricultureFilters
    catalog = service.catalog(AgricultureFilters(department='05', municipality='05001'))
    assert catalog['active_municipality']['name'] == 'MEDELLÍN'
