"""Tests for GeocodingServiceFactory — registry, creation, and fallback chain."""

import pytest

from integration.external_apis.cached_geocoding_service import CachedGeocodingService
from integration.external_apis.geocoding_factory import GeocodingServiceFactory
from integration.external_apis.local_geocoding_service import LocalGeocodingService
from integration.external_apis.nominatim_client import NominatimGeocodingService
from integration.configuration.settings import Settings


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset class-level registry state between tests."""
    GeocodingServiceFactory._initialized = False
    GeocodingServiceFactory._service_registry = {}
    yield
    GeocodingServiceFactory._initialized = False
    GeocodingServiceFactory._service_registry = {}


def test_create_local_service():
    svc = GeocodingServiceFactory.create_service("local")
    assert isinstance(svc, LocalGeocodingService)
    assert svc.is_service_available()


def test_create_nominatim_returns_cached_wrapper():
    """Nominatim must always be wrapped in CachedGeocodingService."""
    svc = GeocodingServiceFactory.create_service("nominatim", settings=Settings())
    assert isinstance(svc, CachedGeocodingService)
    # Delegate should be Nominatim
    assert isinstance(svc._delegate, NominatimGeocodingService)


def test_invalid_provider_raises():
    with pytest.raises(ValueError, match="Unsupported geocoding provider"):
        GeocodingServiceFactory.create_service("unknown_provider")


def test_get_available_services():
    services = GeocodingServiceFactory.get_available_services()
    assert "local" in services
    assert "nominatim" in services


def test_register_custom_provider():
    GeocodingServiceFactory.register_service("local", LocalGeocodingService)
    services = GeocodingServiceFactory.get_available_services()
    assert "local" in services


def test_create_from_settings_defaults_to_nominatim():
    settings = Settings()
    settings.geocoding_provider = "nominatim"
    svc = GeocodingServiceFactory.create_from_settings(settings=settings)
    # Nominatim is always available → no fallback
    assert isinstance(svc, CachedGeocodingService)


def test_create_from_settings_fallback_to_local_on_unavailable():
    """If the configured provider reports unavailable, fall back to local."""
    from integration.external_apis.nominatim_client import NominatimGeocodingService

    class UnavailableGeocoder(NominatimGeocodingService):
        def is_service_available(self) -> bool:
            return False

    GeocodingServiceFactory._ensure_registry()
    GeocodingServiceFactory._service_registry["unavailable"] = UnavailableGeocoder

    settings = Settings()
    settings.geocoding_provider = "unavailable"
    svc = GeocodingServiceFactory.create_from_settings(settings=settings)
    assert isinstance(svc, LocalGeocodingService)
