"""Application-layer integration tests for chat endpoint with NLU payload contract."""

import pytest
from fastapi.testclient import TestClient

from presentation.fastapi_factory import create_application
from shared.utils.dependencies import get_backend_adapter, get_conversation_service


class FakeBackendService:
    async def process_query(self, transcription: str, active_profile_id=None):
        del transcription, active_profile_id
        return {
            "ai_response": "Encontré actividades accesibles para Valencia.",
            "intent": "event_search",
            "entities": {
                "destination": "Valencia",
                "accessibility": "wheelchair",
                "location_ner": {
                    "status": "ok",
                    "locations": ["Valencia"],
                    "top_location": "Valencia",
                    "provider": "spacy",
                    "model": "es_core_news_md",
                    "language": "es",
                },
            },
            "pipeline_steps": [
                {
                    "name": "NLU",
                    "tool": "tourism_nlu",
                    "status": "completed",
                    "duration_ms": 120,
                    "summary": "event_search",
                },
                {
                    "name": "LocationNER",
                    "tool": "location_ner",
                    "status": "completed",
                    "duration_ms": 50,
                    "summary": "status=ok, locations=1",
                },
            ],
            "metadata": {
                "timestamp": "2026-03-02T20:00:00",
                "session_type": "test",
                "language": "es-ES",
                "tool_outputs": {
                    "nlu": {
                        "status": "ok",
                        "intent": "event_search",
                        "confidence": 0.9,
                        "entities": {
                            "destination": "Valencia",
                            "accessibility": "wheelchair",
                        },
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "analysis_version": "nlu_v3.0",
                        "latency_ms": 120,
                        "alternatives": [],
                    },
                    "location_ner": {
                        "status": "ok",
                        "locations": ["Valencia"],
                        "top_location": "Valencia",
                        "provider": "spacy",
                        "model": "es_core_news_md",
                        "language": "es",
                    },
                },
                "tool_results_parsed": {
                    "nlu": {
                        "intent": "event_search",
                        "confidence": 0.9,
                        "status": "ok",
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "entities": {
                            "destination": "Valencia",
                            "accessibility": "wheelchair",
                        },
                    }
                },
            },
            "tourism_data": None,
        }

    async def get_system_status(self):
        return {"status": "ok"}

    async def clear_conversation(self):
        return True


class FakeConversationService:
    async def add_message(self, user_message: str, ai_response: str, session_id=None):
        del user_message, ai_response
        return session_id or "test-session"


@pytest.mark.integration
def test_chat_message_includes_nlu_contract_fields():
    """Chat endpoint should expose stable NLU payload while keeping backward compatible fields."""
    app = create_application()
    app.dependency_overrides[get_backend_adapter] = lambda: FakeBackendService()
    app.dependency_overrides[get_conversation_service] = lambda: FakeConversationService()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "Recomiéndame planes accesibles en Valencia"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["ai_response"]
    assert payload["session_id"]
    assert payload["intent"] == "event_search"
    assert payload["entities"]["destination"] == "Valencia"

    tool_outputs = payload["metadata"]["tool_outputs"]
    assert tool_outputs["nlu"]["intent"] == "event_search"
    assert tool_outputs["nlu"]["provider"] == "openai"
    assert tool_outputs["nlu"]["entities"]["destination"] == "Valencia"
    assert tool_outputs["location_ner"]["top_location"] == "Valencia"

    assert any(step["name"] == "NLU" for step in (payload.get("pipeline_steps") or []))
