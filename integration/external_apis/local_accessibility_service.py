"""Local fallback accessibility service using existing ACCESSIBILITY_DB mock data."""

from typing import Optional

import structlog

from business.domains.tourism.data.accessibility_data import (
    ACCESSIBILITY_DB,
    DEFAULT_ACCESSIBILITY,
)
from shared.interfaces.accessibility_interface import AccessibilityServiceInterface
from shared.models.tool_models import AccessibilityInfo

logger = structlog.get_logger(__name__)


class LocalAccessibilityService(AccessibilityServiceInterface):
    """Fallback implementation that uses local ACCESSIBILITY_DB data."""

    async def enrich_accessibility(
        self,
        place_name: str,
        place_id: Optional[str] = None,
        location: Optional[str] = None,
        language: str = "es",
    ) -> AccessibilityInfo:
        data = self._find_accessibility(place_name)
        return AccessibilityInfo(
            accessibility_level=data.get("accessibility_level", "general"),
            venue_rating=data.get("venue_rating"),
            facilities=data.get("facilities", []),
            accessibility_score=data.get("accessibility_score", 0.0),
            certification=data.get("certification"),
            source="local_db",
        )

    def is_service_available(self) -> bool:
        return True

    def get_service_info(self) -> dict:
        return {
            "provider": "local_db",
            "available": True,
            "venues_count": len(ACCESSIBILITY_DB),
        }

    @staticmethod
    def _find_accessibility(place_name: str) -> dict:
        for key in ACCESSIBILITY_DB:
            if key.lower() in place_name.lower() or place_name.lower() in key.lower():
                return ACCESSIBILITY_DB[key]
        return DEFAULT_ACCESSIBILITY
