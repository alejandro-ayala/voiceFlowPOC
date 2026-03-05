"""Factory for creating pluggable Directions service providers."""

from __future__ import annotations

from typing import Dict, Optional, Type

import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.directions_interface import DirectionsServiceInterface

logger = structlog.get_logger(__name__)


class DirectionsServiceFactory:
    """Factory with registry and fallback chain for Directions services."""

    _service_registry: Dict[str, Type[DirectionsServiceInterface]] = {}
    _initialized = False

    @classmethod
    def _ensure_registry(cls) -> None:
        if cls._initialized:
            return
        from integration.external_apis.google_directions_client import (
            GoogleDirectionsService,
        )
        from integration.external_apis.local_directions_service import (
            LocalDirectionsService,
        )
        from integration.external_apis.openroute_client import (
            OpenRouteDirectionsService,
        )

        cls._service_registry = {
            "google": GoogleDirectionsService,
            "openroute": OpenRouteDirectionsService,
            "local": LocalDirectionsService,
        }
        cls._initialized = True

    @classmethod
    def create_service(
        cls,
        provider: str,
        settings: Optional[Settings] = None,
        resilience: Optional[ResilienceManager] = None,
    ) -> DirectionsServiceInterface:
        cls._ensure_registry()
        normalized = provider.lower().strip()
        if normalized not in cls._service_registry:
            available = ", ".join(sorted(cls._service_registry.keys()))
            raise ValueError(f"Unsupported directions provider: {provider}. Available: {available}")

        service_class = cls._service_registry[normalized]
        logger.info("creating_directions_provider", provider=normalized)

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
    ) -> DirectionsServiceInterface:
        runtime = settings or Settings()
        configured = runtime.directions_provider

        service = cls.create_service(configured, settings=runtime, resilience=resilience)
        if service.is_service_available():
            return service

        logger.warning(
            "directions_provider_unavailable_falling_back",
            configured=configured,
            fallback="local",
        )
        return cls.create_service("local")

    @classmethod
    def register_service(cls, name: str, service_class: Type[DirectionsServiceInterface]) -> None:
        cls._ensure_registry()
        cls._service_registry[name.lower().strip()] = service_class
        logger.info("registered_directions_provider", provider=name)

    @classmethod
    def get_available_services(cls) -> list[str]:
        cls._ensure_registry()
        return sorted(cls._service_registry.keys())
