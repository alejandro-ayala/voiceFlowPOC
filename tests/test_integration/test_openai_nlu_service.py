"""Integration tests for OpenAI NLU provider with mocked OpenAI client."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from integration.configuration.settings import Settings
from integration.external_apis.openai_nlu_service import OpenAINLUService


def _build_mock_response(arguments: dict) -> SimpleNamespace:
    tool_call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps(arguments)))
    message = SimpleNamespace(tool_calls=[tool_call])
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _build_success_client(arguments: dict) -> SimpleNamespace:
    async def create(**kwargs):
        del kwargs
        return _build_mock_response(arguments)

    completions = SimpleNamespace(create=create)
    chat = SimpleNamespace(completions=completions)
    return SimpleNamespace(chat=chat)


def _build_failing_client() -> SimpleNamespace:
    async def create(**kwargs):
        del kwargs
        raise RuntimeError("api failure")

    completions = SimpleNamespace(create=create)
    chat = SimpleNamespace(completions=completions)
    return SimpleNamespace(chat=chat)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_nlu_service_parses_function_calling_response(monkeypatch):
    """Provider should parse OpenAI function call JSON into NLUResult."""
    fake_client = _build_success_client(
        {
            "intent": "route_planning",
            "confidence": 0.95,
            "destination": "Museo del Prado",
            "accessibility": "wheelchair",
            "alternative_intent": "event_search",
            "alternative_confidence": 0.44,
        }
    )

    monkeypatch.setattr(
        "integration.external_apis.openai_nlu_service.AsyncOpenAI",
        lambda api_key: fake_client,
    )

    settings = Settings(openai_api_key="dummy", nlu_openai_model="gpt-4o-mini")
    service = OpenAINLUService(settings=settings)

    result = await service.analyze_text("Cómo llego al Prado?")

    assert result.status == "ok"
    assert result.intent == "route_planning"
    assert result.entities.destination == "Museo del Prado"
    assert result.entities.accessibility == "wheelchair"
    assert result.provider == "openai"
    assert len(result.alternatives) == 1
    assert result.alternatives[0].intent == "event_search"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_nlu_service_returns_error_on_provider_exception(monkeypatch):
    """Provider should degrade to error status when OpenAI call fails."""
    failing_client = _build_failing_client()

    monkeypatch.setattr(
        "integration.external_apis.openai_nlu_service.AsyncOpenAI",
        lambda api_key: failing_client,
    )

    service = OpenAINLUService(settings=Settings(openai_api_key="dummy"))
    result = await service.analyze_text("Necesito un hotel")

    assert result.status == "error"
    assert result.provider == "openai"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_nlu_service_returns_error_on_empty_input():
    """Empty input should return canonical error result."""
    service = OpenAINLUService(settings=Settings(openai_api_key="dummy"))
    result = await service.analyze_text("   ")

    assert result.status == "error"
    assert result.intent == "general_query"


@pytest.mark.integration
def test_openai_nlu_service_unavailable_without_api_key():
    """Provider must report unavailable if API key is missing."""
    service = OpenAINLUService(settings=Settings(openai_api_key=None))
    assert service.is_service_available() is False
