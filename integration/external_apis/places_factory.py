"""Factory for creating pluggable Places service providers."""

from __future__ import annotations

from typing import Dict, Optional, Type

import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.places_interface import PlacesServiceInterface

logger = structlog.get_logger(__name__)


class PlacesServiceFactory:
    """Factory with registry and fallback chain for Places services."""

    _service_registry: Dict[str, Type[PlacesServiceInterface]] = {}
    _initialized = False

    @classmethod
    def _ensure_registry(cls) -> None:
        if cls._initialized:
            return
        from integration.external_apis.google_places_client import GooglePlacesService
        from integration.external_apis.local_places_service import LocalPlacesService

        cls._service_registry = {
            "google": GooglePlacesService,
            "local": LocalPlacesService,
        }
        cls._initialized = True

    @classmethod
    def create_service(
        cls,
        provider: str,
        settings: Optional[Settings] = None,
        resilience: Optional[ResilienceManager] = None,
    ) -> PlacesServiceInterface:
        cls._ensure_registry()
        normalized = provider.lower().strip()
        if normalized not in cls._service_registry:
            available = ", ".join(sorted(cls._service_registry.keys()))
            raise ValueError(f"Unsupported places provider: {provider}. Available: {available}")

        service_class = cls._service_registry[normalized]
        logger.info("creating_places_provider", provider=normalized)

        kwargs: dict = {}
        if normalized != "local":
            runtime = settings or Settings()
            kwargs["settings"] = runtime
            if resilience:
                kwargs["resilience"] = resilience
        return service_class(**kwargs)

    @classmethod
    def create_from_settings(
        cls,
        settings: Optional[Settings] = None,
        resilience: Optional[ResilienceManager] = None,
    ) -> PlacesServiceInterface:
        runtime = settings or Settings()
        configured = runtime.places_provider

        service = cls.create_service(configured, settings=runtime, resilience=resilience)
        if service.is_service_available():
            return service

        logger.warning(
            "places_provider_unavailable_falling_back",
            configured=configured,
            fallback="local",
        )
        return cls.create_service("local")

    @classmethod
    def register_service(cls, name: str, service_class: Type[PlacesServiceInterface]) -> None:
        cls._ensure_registry()
        cls._service_registry[name.lower().strip()] = service_class
        logger.info("registered_places_provider", provider=name)

    @classmethod
    def get_available_services(cls) -> list[str]:
        cls._ensure_registry()
        return sorted(cls._service_registry.keys())
