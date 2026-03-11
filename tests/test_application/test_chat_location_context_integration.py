"""Application-layer integration tests for runtime location context propagation."""

import pytest
from fastapi.testclient import TestClient

from presentation.fastapi_factory import create_application
from shared.utils.dependencies import get_backend_adapter, get_conversation_service


class CapturingBackendService:
    def __init__(self):
        self.last_runtime_context = None

    async def process_query(self, transcription: str, active_profile_id=None, runtime_context=None):
        del transcription, active_profile_id
        self.last_runtime_context = runtime_context
        return {
            "ai_response": "ok",
            "intent": "route_planning",
            "entities": {},
            "pipeline_steps": [],
            "metadata": {},
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
def test_chat_message_passes_runtime_location_and_debug_mock_context():
    """Chat endpoint should pass location + debug mock context to backend adapter."""
    app = create_application()
    backend = CapturingBackendService()
    app.dependency_overrides[get_backend_adapter] = lambda: backend
    app.dependency_overrides[get_conversation_service] = lambda: FakeConversationService()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/message",
            json={
                "message": "Llévame al Prado",
                "context": {
                    "source": "web_ui",
                    "debug_mock_location": "40.4168,-3.7038",
                    "location": {
                        "latitude": 41.3874,
                        "longitude": 2.1686,
                        "accuracy_meters": 24.0,
                        "source": "browser_geolocation",
                    },
                },
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert backend.last_runtime_context is not None
    assert backend.last_runtime_context["debug_mock_location"] == "40.4168,-3.7038"
    assert backend.last_runtime_context["location"]["latitude"] == 41.3874
    assert backend.last_runtime_context["location"]["longitude"] == 2.1686
