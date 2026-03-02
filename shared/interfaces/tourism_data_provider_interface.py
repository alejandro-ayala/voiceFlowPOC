"""Abstract provider contract for high-level tourism capabilities."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class TourismDataProviderInterface(ABC):
    """Normalize tourism data access across external providers."""

    @abstractmethod
    def is_service_available(self) -> bool:
        """Return provider availability status."""

    @abstractmethod
    def get_service_info(self) -> dict[str, Any]:
        """Return provider metadata for observability."""

    @abstractmethod
    def get_accessibility_insights(
        self,
        destination: Optional[str],
        accessibility_need: Optional[str],
        profile_context: Optional[dict[str, Any]] = None,
        language: str = "es",
    ) -> dict[str, Any]:
        """Return normalized accessibility payload for a destination."""

    @abstractmethod
    def plan_routes(
        self,
        origin_text: Optional[str],
        destination: Optional[str],
        accessibility_need: Optional[str],
        profile_context: Optional[dict[str, Any]] = None,
        language: str = "es",
    ) -> dict[str, Any]:
        """Return normalized route planning payload."""

    @abstractmethod
    def get_tourism_info(
        self,
        destination: Optional[str],
        query_text: Optional[str],
        profile_context: Optional[dict[str, Any]] = None,
        language: str = "es",
    ) -> dict[str, Any]:
        """Return normalized tourism venue payload."""
