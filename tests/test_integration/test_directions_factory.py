"""Tests for DirectionsServiceFactory."""

import pytest

from integration.external_apis.directions_factory import DirectionsServiceFactory
from integration.external_apis.local_directions_service import LocalDirectionsService


class TestDirectionsServiceFactory:
    def test_create_local_provider(self):
        service = DirectionsServiceFactory.create_service("local")
        assert isinstance(service, LocalDirectionsService)
        assert service.is_service_available() is True

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported directions provider"):
            DirectionsServiceFactory.create_service("nonexistent")

    def test_available_services(self):
        services = DirectionsServiceFactory.get_available_services()
        assert "local" in services
        assert "google" in services
        assert "openroute" in services

    def test_create_from_settings_defaults_to_local(self):
        service = DirectionsServiceFactory.create_from_settings()
        assert isinstance(service, LocalDirectionsService)
