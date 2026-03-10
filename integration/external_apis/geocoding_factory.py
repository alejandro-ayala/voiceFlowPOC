"""Factory for creating pluggable Geocoding service providers."""

from __future__ import annotations

from typing import Dict, Optional, Type

import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.geocoding_interface import GeocodingServiceInterface

logger = structlog.get_logger(__name__)


class GeocodingServiceFactory:
    """Factory with registry and fallback chain for Geocoding services.

    Follows the same Factory + Registry + Fallback pattern used by
    PlacesServiceFactory, DirectionsServiceFactory, and AccessibilityServiceFactory.

    Registered providers:
        nominatim — Nominatim/OSM, free, wrapped in CachedGeocodingService (TTL 1h)
        local     — Static Madrid venue lookup, always available, zero latency
    """

    _service_registry: Dict[str, Type[GeocodingServiceInterface]] = {}
    _initialized = False

    @classmethod
    def _ensure_registry(cls) -> None:
        if cls._initialized:
            return
        from integration.external_apis.local_geocoding_service import LocalGeocodingService
        from integration.external_apis.nominatim_client import NominatimGeocodingService

        cls._service_registry = {
            "nominatim": NominatimGeocodingService,
            "local": LocalGeocodingService,
        }
        cls._initialized = True

    @classmethod
    def create_service(
        cls,
        provider: str,
        settings: Optional[Settings] = None,
        resilience: Optional[ResilienceManager] = None,
    ) -> GeocodingServiceInterface:
        cls._ensure_registry()
        normalized = provider.lower().strip()
        if normalized not in cls._service_registry:
            available = ", ".join(sorted(cls._service_registry.keys()))
            raise ValueError(
                f"Unsupported geocoding provider: {provider!r}. Available: {available}"
            )

        logger.info("creating_geocoding_provider", provider=normalized)
        service_class = cls._service_registry[normalized]

        if normalized == "local":
            return service_class()

        # Real providers: inject settings-derived params
        runtime = settings or Settings()
        kwargs: dict = {
            "timeout": runtime.tool_timeout_seconds,
        }
        if resilience:
            kwargs["resilience"] = resilience

        raw_service = service_class(**kwargs)

        # Wrap Nominatim in cache to respect 1 req/s rate limit
        if normalized == "nominatim":
            from integration.external_apis.cached_geocoding_service import CachedGeocodingService

            ttl = getattr(runtime, "geocoding_cache_ttl", 3600)
            return CachedGeocodingService(raw_service, ttl_seconds=ttl)

        return raw_service

    @classmethod
    def create_from_settings(
        cls,
        settings: Optional[Settings] = None,
        resilience: Optional[ResilienceManager] = None,
    ) -> GeocodingServiceInterface:
        runtime = settings or Settings()
        configured = getattr(runtime, "geocoding_provider", "nominatim")

        service = cls.create_service(configured, settings=runtime, resilience=resilience)
        if service.is_service_available():
            return service

        logger.warning(
            "geocoding_provider_unavailable_falling_back",
            configured=configured,
            fallback="local",
        )
        return cls.create_service("local")

    @classmethod
    def register_service(
        cls,
        name: str,
        service_class: Type[GeocodingServiceInterface],
    ) -> None:
        """Register a new provider (OCP: open for extension)."""
        cls._ensure_registry()
        cls._service_registry[name.lower().strip()] = service_class
        logger.info("registered_geocoding_provider", provider=name)

    @classmethod
    def get_available_services(cls) -> list[str]:
        cls._ensure_registry()
        return sorted(cls._service_registry.keys())
