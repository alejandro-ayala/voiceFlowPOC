"""Tests for PlacesServiceFactory."""

import pytest

from integration.external_apis.local_places_service import LocalPlacesService
from integration.external_apis.places_factory import PlacesServiceFactory


class TestPlacesServiceFactory:
    def test_create_local_provider(self):
        service = PlacesServiceFactory.create_service("local")
        assert isinstance(service, LocalPlacesService)
        assert service.is_service_available() is True

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported places provider"):
            PlacesServiceFactory.create_service("nonexistent")

    def test_available_services_includes_local_and_google(self):
        services = PlacesServiceFactory.get_available_services()
        assert "local" in services
        assert "google" in services

    def test_create_from_settings_defaults_to_local(self):
        service = PlacesServiceFactory.create_from_settings()
        assert isinstance(service, LocalPlacesService)

    def test_get_service_info(self):
        service = PlacesServiceFactory.create_service("local")
        info = service.get_service_info()
        assert info["provider"] == "local_db"
        assert info["available"] is True
