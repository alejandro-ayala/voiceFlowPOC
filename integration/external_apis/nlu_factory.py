"""Factory for creating pluggable NLU providers."""

from __future__ import annotations

from typing import Dict, Optional, Type

import structlog

from integration.configuration.settings import Settings
from integration.external_apis.keyword_nlu_service import KeywordNLUService
from integration.external_apis.openai_nlu_service import OpenAINLUService
from shared.interfaces.nlu_interface import NLUServiceInterface

logger = structlog.get_logger(__name__)


class NLUServiceFactory:
    """Factory with registry and fallback chain for NLU services."""

    _service_registry: Dict[str, Type[NLUServiceInterface]] = {
        "openai": OpenAINLUService,
        "keyword": KeywordNLUService,
    }

    @classmethod
    def create_service(cls, provider: str, **kwargs) -> NLUServiceInterface:
        normalized_provider = provider.lower().strip()
        if normalized_provider not in cls._service_registry:
            available = ", ".join(sorted(cls._service_registry.keys()))
            raise ValueError(f"Unsupported NLU provider: {provider}. Available providers: {available}")

        service_class = cls._service_registry[normalized_provider]
        logger.info("creating_nlu_provider", provider=normalized_provider)
        return service_class(**kwargs)

    @classmethod
    def create_from_settings(cls, settings: Optional[Settings] = None) -> NLUServiceInterface:
        runtime_settings = settings or Settings()
        configured_provider = runtime_settings.nlu_provider

        service = cls.create_service(configured_provider, settings=runtime_settings)
        if service.is_service_available():
            return service

        logger.warning(
            "nlu_provider_unavailable_falling_back",
            configured=configured_provider,
            fallback="keyword",
        )
        return cls.create_service("keyword", settings=runtime_settings)

    @classmethod
    def register_service(cls, name: str, service_class: Type[NLUServiceInterface]) -> None:
        normalized_name = name.lower().strip()
        cls._service_registry[normalized_name] = service_class
        logger.info("registered_nlu_provider", provider=normalized_name)

    @classmethod
    def get_available_services(cls) -> list[str]:
        return sorted(cls._service_registry.keys())
