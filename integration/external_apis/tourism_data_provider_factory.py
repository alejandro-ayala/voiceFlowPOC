"""Factory for high-level tourism data providers."""

from __future__ import annotations

from typing import Optional

import structlog

from integration.configuration.settings import Settings
from integration.external_apis.mock_tourism_data_provider import MockTourismDataProvider
from shared.interfaces.tourism_data_provider_interface import TourismDataProviderInterface

logger = structlog.get_logger(__name__)


class TourismDataProviderFactory:
    """Creates tourism data providers from runtime configuration."""

    @staticmethod
    def create_from_settings(settings: Optional[Settings] = None) -> Optional[TourismDataProviderInterface]:
        runtime = settings or Settings()

        if not runtime.high_level_tools_enabled:
            logger.info("high_level_tools_disabled")
            return None

        provider_name = (runtime.tourism_data_provider or "mock").strip().lower()

        if provider_name == "mock":
            provider = MockTourismDataProvider()
            logger.info("high_level_tools_provider_selected", provider="mock")
            return provider

        logger.warning(
            "high_level_tools_provider_unknown_fallback_mock",
            provider=provider_name,
        )
        return MockTourismDataProvider()
