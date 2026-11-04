from fastapi.testclient import TestClient

from app.api.rate_limit import SlidingWindowRateLimiter
from app.core.config import Settings
from app.main import create_app


def test_no_key_validation_size_and_rate_limit(monkeypatch):
    from app.api.v1 import assistant
    monkeypatch.setattr(assistant, 'limiter', SlidingWindowRateLimiter())
    client = TestClient(create_app(Settings(assistant_provider='openai', openai_api_key=None)))
    assert client.post('/api/v1/assistant/query', json={'question': ' '}).status_code == 422
    response = client.post('/api/v1/assistant/query', json={'question': 'café'})
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'ASSISTANT_NOT_CONFIGURED'
    assert client.post('/api/v1/assistant/query', content='x'*24001).status_code == 413
    for _ in range(7):
        client.post('/api/v1/assistant/query', json={'question': 'café'})
    response = client.post('/api/v1/assistant/query', json={'question': 'café'})
    assert response.status_code == 429
    assert int(response.headers['Retry-After']) > 0


def test_cors_allows_chat_post():
    client = TestClient(create_app(Settings(assistant_provider='openai', openai_api_key=None)))
    response = client.options('/api/v1/assistant/query', headers={
        'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    assert response.status_code == 200
    assert 'POST' in response.headers['access-control-allow-methods']


def test_database_failure_is_safe_and_recoverable(monkeypatch):
    from app.api.v1 import assistant
    from sqlalchemy.exc import OperationalError
    monkeypatch.setattr(assistant, 'limiter', SlidingWindowRateLimiter())
    def unavailable(*args):
        raise OperationalError('secret database query', {}, Exception('private detail'))
    monkeypatch.setattr(assistant, 'answer_question', unavailable)
    client = TestClient(create_app(Settings(openai_api_key='test-only-placeholder')))
    response = client.post('/api/v1/assistant/query', json={'question': 'café'})
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'DATA_UNAVAILABLE'
    assert 'private' not in response.text
