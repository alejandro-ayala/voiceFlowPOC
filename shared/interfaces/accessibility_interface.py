"""Accessibility service interface contract for accessibility data enrichment."""

from abc import ABC, abstractmethod
from typing import Optional

from shared.models.tool_models import AccessibilityInfo


class AccessibilityServiceInterface(ABC):
    """Contract for accessibility enrichment services (Google Places, Overpass/OSM, etc.)."""

    @abstractmethod
    async def enrich_accessibility(
        self,
        place_name: str,
        place_id: Optional[str] = None,
        location: Optional[str] = None,
        language: str = "es",
    ) -> AccessibilityInfo:
        """Get accessibility data for a place from external sources."""
        ...

    @abstractmethod
    def is_service_available(self) -> bool:
        """Report if the provider is ready (API key set, etc.)."""
        ...

    @abstractmethod
    def get_service_info(self) -> dict:
        """Return provider metadata: name, status, data sources."""
        ...

    def get_debug_snapshot(self) -> Optional[dict]:
        """Return latest provider debug payload when available."""
        return None
