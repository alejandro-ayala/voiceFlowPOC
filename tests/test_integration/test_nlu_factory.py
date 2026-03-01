"""Integration tests for NLU service factory resolution and registry behavior."""

import pytest

from integration.configuration.settings import Settings
from integration.external_apis.keyword_nlu_service import KeywordNLUService
from integration.external_apis.nlu_factory import NLUServiceFactory
from integration.external_apis.openai_nlu_service import OpenAINLUService
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUResult


class DummyNLUService(NLUServiceInterface):
    async def analyze_text(
        self,
        text: str,
        language: str | None = None,
        profile_context: dict | None = None,
    ) -> NLUResult:
        del text, language, profile_context
        return NLUResult(intent="general_query", provider="dummy")

    def is_service_available(self) -> bool:
        return True

    def get_supported_languages(self) -> list[str]:
        return ["es"]

    def get_service_info(self) -> dict:
        return {"provider": "dummy", "available": True}


@pytest.mark.integration
def test_nlu_factory_create_openai_service_from_settings():
    """Factory should build OpenAI provider when configured and available."""
    settings = Settings(nlu_provider="openai", openai_api_key="dummy")

    service = NLUServiceFactory.create_from_settings(settings)

    assert isinstance(service, OpenAINLUService)


@pytest.mark.integration
def test_nlu_factory_create_keyword_service_from_settings():
    """Factory should build keyword provider when configured."""
    settings = Settings(nlu_provider="keyword")

    service = NLUServiceFactory.create_from_settings(settings)

    assert isinstance(service, KeywordNLUService)


@pytest.mark.integration
def test_nlu_factory_raises_for_unknown_provider():
    """Unknown providers should raise explicit errors."""
    with pytest.raises(ValueError):
        NLUServiceFactory.create_service("unknown_nlu_provider")


@pytest.mark.integration
def test_nlu_factory_falls_back_to_keyword_if_openai_unavailable():
    """Factory should auto-fallback to keyword when OpenAI provider is unavailable."""
    settings = Settings(nlu_provider="openai", openai_api_key=None)

    service = NLUServiceFactory.create_from_settings(settings)

    assert isinstance(service, KeywordNLUService)


@pytest.mark.integration
def test_nlu_factory_register_custom_provider_and_create():
    """Custom NLU provider registration should be available through factory APIs."""
    provider_name = "dummy_nlu_test_provider"
    NLUServiceFactory.register_service(provider_name, DummyNLUService)

    service = NLUServiceFactory.create_service(provider_name)

    assert isinstance(service, DummyNLUService)
    assert provider_name in NLUServiceFactory.get_available_services()
