"""Factory for creating pluggable Accessibility service providers."""

from __future__ import annotations

from typing import Dict, Optional, Type

import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.accessibility_interface import AccessibilityServiceInterface
from shared.interfaces.geocoding_interface import GeocodingServiceInterface

logger = structlog.get_logger(__name__)


class AccessibilityServiceFactory:
    """Factory with registry and fallback chain for Accessibility services."""

    _service_registry: Dict[str, Type[AccessibilityServiceInterface]] = {}
    _initialized = False

    @classmethod
    def _ensure_registry(cls) -> None:
        if cls._initialized:
            return
        from integration.external_apis.local_accessibility_service import (
            LocalAccessibilityService,
        )
        from integration.external_apis.overpass_client import (
            OverpassAccessibilityService,
        )

        cls._service_registry = {
            "overpass": OverpassAccessibilityService,
            "local": LocalAccessibilityService,
        }
        cls._initialized = True

    @classmethod
    def create_service(
        cls,
        provider: str,
        settings: Optional[Settings] = None,
        resilience: Optional[ResilienceManager] = None,
        geocoding_service: Optional[GeocodingServiceInterface] = None,
    ) -> AccessibilityServiceInterface:
        cls._ensure_registry()
        normalized = provider.lower().strip()
        if normalized not in cls._service_registry:
            available = ", ".join(sorted(cls._service_registry.keys()))
            raise ValueError(f"Unsupported accessibility provider: {provider}. Available: {available}")

        service_class = cls._service_registry[normalized]
        logger.info("creating_accessibility_provider", provider=normalized)

        kwargs: dict = {}
        if normalized != "local":
            runtime = settings or Settings()
            kwargs["settings"] = runtime
            if resilience:
                kwargs["resilience"] = resilience
            if normalized == "overpass" and geocoding_service:
                kwargs["geocoding_service"] = geocoding_service
        return service_class(**kwargs)

    @classmethod
    def create_from_settings(
        cls,
        settings: Optional[Settings] = None,
        resilience: Optional[ResilienceManager] = None,
        geocoding_service: Optional[GeocodingServiceInterface] = None,
    ) -> AccessibilityServiceInterface:
        runtime = settings or Settings()
        configured = runtime.accessibility_provider

        service = cls.create_service(
            configured,
            settings=runtime,
            resilience=resilience,
            geocoding_service=geocoding_service,
        )
        if service.is_service_available():
            return service

        logger.warning(
            "accessibility_provider_unavailable_falling_back",
            configured=configured,
            fallback="local",
        )
        return cls.create_service("local")

    @classmethod
    def register_service(cls, name: str, service_class: Type[AccessibilityServiceInterface]) -> None:
        cls._ensure_registry()
        cls._service_registry[name.lower().strip()] = service_class
        logger.info("registered_accessibility_provider", provider=name)

    @classmethod
    def get_available_services(cls) -> list[str]:
        cls._ensure_registry()
        return sorted(cls._service_registry.keys())
