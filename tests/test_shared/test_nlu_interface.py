"""Unit tests for NLU interface contract."""

import inspect

import pytest

from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUResult


class MockNLUService(NLUServiceInterface):
    """Concrete implementation used to validate contract compliance."""

    async def analyze_text(
        self,
        text: str,
        language: str | None = None,
        profile_context: dict | None = None,
    ) -> NLUResult:
        return NLUResult(intent="general_query")

    def is_service_available(self) -> bool:
        return True

    def get_supported_languages(self) -> list[str]:
        return ["es", "en"]

    def get_service_info(self) -> dict:
        return {"provider": "mock"}


@pytest.mark.unit
def test_nlu_interface_is_abstract_contract():
    """NLUServiceInterface must stay abstract and expose expected methods."""
    assert inspect.isabstract(NLUServiceInterface)

    expected_methods = {
        "analyze_text",
        "is_service_available",
        "get_supported_languages",
        "get_service_info",
    }
    assert expected_methods.issubset(set(NLUServiceInterface.__abstractmethods__))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nlu_interface_concrete_implementation_satisfies_contract():
    """A concrete class implementing all methods should be instantiable and usable."""
    service = MockNLUService()

    result = await service.analyze_text("hola")

    assert isinstance(result, NLUResult)
    assert service.is_service_available() is True
    assert service.get_supported_languages() == ["es", "en"]
    assert service.get_service_info()["provider"] == "mock"
