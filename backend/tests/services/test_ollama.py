import json
from io import BytesIO

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.assistant import AssistantRequest
from app.services.assistant import ollama


def test_local_action_uses_schema_and_validates_response(monkeypatch):
    # Use the actual contract rather than trusting free-form model text.
    from app.schemas.assistant import SelectedAction

    action = SelectedAction(action="rank").model_dump()
    captured = {}

    def fake_open(request, timeout):
        captured.update(json.loads(request.data))
        assert request.full_url == "http://localhost:11434/api/chat"
        assert timeout == 180
        return BytesIO(json.dumps({"message": {"content": json.dumps(action)}}).encode())

    monkeypatch.setattr(ollama, "urlopen", fake_open)
    result = ollama.select_local_action(
        Settings(), AssistantRequest(question="¿Dónde se cultiva más café?"), 2025, {}
    )
    assert result.action == "rank"
    assert captured["stream"] is False
    assert captured["think"] is False
    assert captured["format"]["additionalProperties"] is False


def test_local_action_rejects_untrusted_extra_fields(monkeypatch):
    monkeypatch.setattr(
        ollama,
        "urlopen",
        lambda *a, **k: BytesIO(
            json.dumps(
                {"message": {"content": '{"action":"rank","sql":"DROP TABLE crops"}'}}
            ).encode()
        ),
    )
    with pytest.raises(ValidationError):
        ollama.select_local_action(Settings(), AssistantRequest(question="café"), 2025, {})


def test_local_provider_does_not_require_openai_key(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.rate_limit import SlidingWindowRateLimiter
    from app.api.v1 import assistant
    from app.main import create_app
    from app.schemas.assistant import AssistantResponse

    monkeypatch.setattr(assistant, "limiter", SlidingWindowRateLimiter())
    monkeypatch.setattr(
        assistant,
        "answer_question",
        lambda *args: AssistantResponse(status="no_data", answer="Consulta local ejecutada"),
    )
    client = TestClient(create_app(Settings(assistant_provider="ollama", openai_api_key=None)))
    assert client.post("/api/v1/assistant/query", json={"question": "café"}).status_code == 200
