"""Unit tests for refactored TourismNLUTool with pluggable NLU service delegation."""

import json

import pytest

from business.domains.tourism.tools.nlu_tool import TourismNLUTool
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUEntitySet, NLUResult


class MockNLUService(NLUServiceInterface):
    def __init__(self, available: bool = True, status: str = "ok"):
        self.available = available
        self.status = status

    async def analyze_text(
        self,
        text: str,
        language: str | None = None,
        profile_context: dict | None = None,
    ) -> NLUResult:
        del text, profile_context
        return NLUResult(
            status=self.status,
            intent="route_planning",
            confidence=0.95,
            entities=NLUEntitySet(destination="Museo del Prado", accessibility="wheelchair"),
            provider="mock",
            model="mock-model",
            language=language or "es",
        )

    def is_service_available(self) -> bool:
        return self.available

    def get_supported_languages(self) -> list[str]:
        return ["es"]

    def get_service_info(self) -> dict:
        return {"provider": "mock", "available": self.available}


@pytest.mark.unit
def test_tourism_nlu_tool_delegates_to_injected_service():
    """Tool should delegate to injected NLU service and output expected JSON fields."""
    tool = TourismNLUTool(nlu_service=MockNLUService(available=True, status="ok"))

    result_raw = tool._run("Cómo llego al Prado?")
    result = json.loads(result_raw)

    assert result["intent"] == "route_planning"
    assert result["entities"]["destination"] == "Museo del Prado"
    assert result["entities"]["accessibility"] == "wheelchair"
    assert result["confidence"] == pytest.approx(0.95)
    assert result["provider"] == "mock"


@pytest.mark.unit
def test_tourism_nlu_tool_fallback_when_service_unavailable():
    """Tool should fallback to keyword classification when provider is unavailable."""
    tool = TourismNLUTool(nlu_service=MockNLUService(available=False, status="ok"))

    result_raw = tool._run("Quiero ir al prado")
    result = json.loads(result_raw)

    assert result["provider"] == "keyword"
    assert result["intent"] in {
        "route_planning",
        "general_query",
    }
    assert "entities" in result


@pytest.mark.unit
def test_tourism_nlu_tool_fallback_when_service_returns_error_status():
    """Tool should fallback to keyword classification when service reports error status."""
    tool = TourismNLUTool(nlu_service=MockNLUService(available=True, status="error"))

    result_raw = tool._run("Necesito un restaurante")
    result = json.loads(result_raw)

    assert result["provider"] == "keyword"
    assert result["status"] in {"ok", "fallback"}
    assert "intent" in result
