"""Business integration tests for NLU+NER merge behavior in TourismMultiAgent."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from business.domains.tourism.agent import TourismMultiAgent


@pytest.mark.integration
def test_agent_merges_nlu_and_ner_preferring_nlu_on_real_conflict(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")

    with patch("business.domains.tourism.agent.ChatOpenAI"):
        agent = TourismMultiAgent(openai_api_key="test-key-12345")

    with patch(
        "business.domains.tourism.agent.TourismNLUTool._arun",
        new=AsyncMock(
            return_value=json.dumps(
                {
                    "status": "ok",
                    "intent": "route_planning",
                    "confidence": 0.9,
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "entities": {
                        "destination": "Museo del Prado",
                        "accessibility": "wheelchair",
                        "language": "es",
                    },
                }
            )
        ),
    ), patch(
        "business.domains.tourism.agent.LocationNERTool._arun",
        new=AsyncMock(
            return_value=json.dumps(
                {
                    "status": "ok",
                    "locations": ["Retiro", "Prado"],
                    "top_location": "Retiro",
                    "provider": "spacy",
                    "model": "es_core_news_md",
                    "language": "es",
                }
            )
        ),
    ):
        _, metadata = agent._execute_pipeline("Llévame al Retiro y al Prado")

    entities = metadata["entities"]
    assert entities["destination"] == "Museo del Prado"
    assert entities["resolution_source"]["destination"] == "nlu_preferred"
    assert entities["locations"] == ["Retiro", "Prado"]


@pytest.mark.integration
def test_agent_merges_nlu_and_ner_using_ner_override_for_generic_destination(
    monkeypatch,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")

    with patch("business.domains.tourism.agent.ChatOpenAI"):
        agent = TourismMultiAgent(openai_api_key="test-key-12345")

    with patch(
        "business.domains.tourism.agent.TourismNLUTool._arun",
        new=AsyncMock(
            return_value=json.dumps(
                {
                    "status": "fallback",
                    "intent": "general_query",
                    "confidence": 0.0,
                    "provider": "keyword",
                    "model": "keyword_patterns",
                    "entities": {
                        "destination": "general",
                        "accessibility": "general",
                        "language": "es",
                    },
                }
            )
        ),
    ), patch(
        "business.domains.tourism.agent.LocationNERTool._arun",
        new=AsyncMock(
            return_value=json.dumps(
                {
                    "status": "ok",
                    "locations": ["Valencia"],
                    "top_location": "Valencia",
                    "provider": "spacy",
                    "model": "es_core_news_md",
                    "language": "es",
                }
            )
        ),
    ):
        _, metadata = agent._execute_pipeline("Qué puedo visitar en Valencia")

    entities = metadata["entities"]
    assert entities["destination"] == "Valencia"
    assert entities["resolution_source"]["destination"] == "ner_override"
    assert entities["top_location"] == "Valencia"
