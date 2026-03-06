"""Integration tests for keyword NLU fallback provider."""

import pytest

from integration.configuration.settings import Settings
from integration.external_apis.keyword_nlu_service import KeywordNLUService


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "expected_intent"),
    [
        ("Cómo llegar al Prado en metro", "route_planning"),
        ("Qué conciertos hay hoy", "event_search"),
        ("Restaurante accesible cerca", "restaurant_search"),
        ("Busco hotel en Madrid", "accommodation_search"),
        ("Hola, qué me recomiendas", "general_query"),
    ],
)
async def test_keyword_nlu_classifies_expected_intents(text: str, expected_intent: str):
    """Keyword provider should map common phrases to expected intents."""
    service = KeywordNLUService(settings=Settings())

    result = await service.analyze_text(text)

    assert result.intent == expected_intent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_keyword_nlu_returns_fallback_for_ambiguous_input():
    """Unknown inputs should degrade to general_query with fallback status."""
    service = KeywordNLUService(settings=Settings())

    result = await service.analyze_text("asdf zxcv qwerty")

    assert result.intent == "general_query"
    assert result.status == "fallback"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_keyword_nlu_extracts_destination_and_accessibility():
    """Provider should extract destination and accessibility entities from text."""
    service = KeywordNLUService(settings=Settings())

    result = await service.analyze_text("Quiero ir al prado con silla de ruedas")

    assert result.entities.destination == "Museo del Prado"
    assert result.entities.accessibility == "wheelchair"
