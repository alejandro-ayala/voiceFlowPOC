"""Application-layer integration tests for chat endpoint with NER payload."""

import pytest
from fastapi.testclient import TestClient

from presentation.fastapi_factory import create_application
from shared.utils.dependencies import get_backend_adapter, get_conversation_service


class FakeBackendService:
    async def process_query(self, transcription: str, active_profile_id=None):
        return {
            "ai_response": "Perfecto, encontré opciones accesibles en Barcelona.",
            "intent": "route_planning",
            "entities": {
                "location": "Barcelona",
                "location_ner": {
                    "status": "ok",
                    "locations": ["Barcelona"],
                    "top_location": "Barcelona",
                    "provider": "spacy",
                    "model": "es_core_news_md",
                    "language": "es",
                },
            },
            "pipeline_steps": [
                {
                    "name": "LocationNER",
                    "tool": "location_ner",
                    "status": "completed",
                    "duration_ms": 20,
                    "summary": "status=ok, locations=1",
                }
            ],
            "metadata": {
                "timestamp": "2026-02-23T20:00:00",
                "session_type": "test",
                "language": "es-ES",
                "tool_outputs": {
                    "location_ner": {
                        "status": "ok",
                        "locations": ["Barcelona"],
                        "top_location": "Barcelona",
                        "provider": "spacy",
                        "model": "es_core_news_md",
                        "language": "es",
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
        return session_id or "test-session"


@pytest.mark.integration
def test_chat_message_includes_location_ner_payload_contract():
    """Chat endpoint should preserve NER entities and metadata tool outputs."""
    app = create_application()
    app.dependency_overrides[get_backend_adapter] = lambda: FakeBackendService()
    app.dependency_overrides[get_conversation_service] = lambda: FakeConversationService()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "Quiero turismo cultural en Barcelona"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "success"
    assert payload["intent"] == "route_planning"
    assert payload["entities"]["location_ner"]["status"] == "ok"
    assert payload["entities"]["location_ner"]["top_location"] == "Barcelona"
    assert payload["metadata"]["tool_outputs"]["location_ner"]["locations"] == ["Barcelona"]
    assert any(step["name"] == "LocationNER" for step in (payload.get("pipeline_steps") or []))
