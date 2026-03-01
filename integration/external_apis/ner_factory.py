"""Factory for creating pluggable NER providers."""

import os
from typing import Dict, Optional, Type

import structlog

from integration.configuration.settings import Settings
from integration.external_apis.spacy_ner_service import SpacyNERService
from shared.interfaces.ner_interface import NERServiceInterface

logger = structlog.get_logger(__name__)


class NERServiceFactory:
    """Factory with registry to instantiate NER providers without changing clients."""

    _service_registry: Dict[str, Type[NERServiceInterface]] = {
        "spacy": SpacyNERService,
    }

    @classmethod
    def create_service(cls, provider: str, **kwargs) -> NERServiceInterface:
        """Create NER provider from registered provider name."""
        normalized_provider = provider.lower().strip()
        if normalized_provider not in cls._service_registry:
            available = ", ".join(sorted(cls._service_registry.keys()))
            raise ValueError(f"Unsupported NER provider: {provider}. Available providers: {available}")

        service_class = cls._service_registry[normalized_provider]
        logger.info("Creating NER provider", provider=normalized_provider)
        return service_class(**kwargs)

    @classmethod
    def create_from_settings(cls, settings: Optional[Settings] = None) -> NERServiceInterface:
        """Create provider using pydantic settings (preferred runtime path)."""
        runtime_settings = settings or Settings()
        return cls.create_service(runtime_settings.ner_provider, settings=runtime_settings)

    @classmethod
    def create_from_env(cls) -> NERServiceInterface:
        """Create provider from env vars for bootstrap scripts and ad-hoc usage."""
        provider = os.getenv("VOICEFLOW_NER_PROVIDER") or os.getenv("NER_PROVIDER") or "spacy"
        return cls.create_service(provider, settings=Settings())

    @classmethod
    def register_service(cls, name: str, service_class: Type[NERServiceInterface]) -> None:
        """Register custom NER provider (OCP extension point)."""
        normalized_name = name.lower().strip()
        cls._service_registry[normalized_name] = service_class
        logger.info("Registered NER provider", provider=normalized_name)

    @classmethod
    def get_available_services(cls) -> list[str]:
        """Return registered provider names."""
        return sorted(cls._service_registry.keys())
