"""Integration tests for NER service factory resolution and registry behavior."""

import pytest

from integration.configuration.settings import Settings
from integration.external_apis.ner_factory import NERServiceFactory
from integration.external_apis.spacy_ner_service import SpacyNERService
from shared.interfaces.ner_interface import NERServiceInterface


class DummyNERService(NERServiceInterface):
    async def extract_locations(self, text: str, language: str | None = None):
        return {
            "locations": [],
            "top_location": None,
            "provider": "dummy",
            "model": "dummy-model",
            "language": language or "es",
            "status": "ok",
        }

    def is_service_available(self) -> bool:
        return True

    def get_supported_languages(self) -> list[str]:
        return ["es"]

    def get_service_info(self):
        return {"provider": "dummy", "available": True}


@pytest.mark.integration
def test_ner_factory_create_spacy_service_from_provider_name():
    """Factory must resolve built-in 'spacy' provider."""
    service = NERServiceFactory.create_service("spacy", settings=Settings())
    assert isinstance(service, SpacyNERService)


@pytest.mark.integration
def test_ner_factory_create_from_settings_uses_configured_provider():
    """Factory should honor provider configured in settings."""
    settings = Settings(ner_provider="spacy")
    service = NERServiceFactory.create_from_settings(settings)
    assert isinstance(service, SpacyNERService)


@pytest.mark.integration
def test_ner_factory_register_custom_provider_and_create():
    """Custom provider registration should be available via create_service."""
    provider_name = "dummy_ner_test_provider"
    NERServiceFactory.register_service(provider_name, DummyNERService)

    service = NERServiceFactory.create_service(provider_name)
    assert isinstance(service, DummyNERService)
    assert provider_name in NERServiceFactory.get_available_services()


@pytest.mark.integration
def test_ner_factory_raises_for_unknown_provider():
    """Unknown provider should raise explicit error."""
    with pytest.raises(ValueError):
        NERServiceFactory.create_service("unknown_provider")
