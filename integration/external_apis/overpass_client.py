"""Overpass API (OpenStreetMap) client for accessibility enrichment."""

from typing import Optional

import httpx
import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.accessibility_interface import AccessibilityServiceInterface
from shared.models.tool_models import AccessibilityInfo

logger = structlog.get_logger(__name__)

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL template: find wheelchair-tagged nodes near a location
_QUERY_TEMPLATE = """
[out:json][timeout:5];
(
  node["wheelchair"](around:200,{lat},{lng});
  way["wheelchair"](around:200,{lat},{lng});
);
out body;
"""


class OverpassAccessibilityService(AccessibilityServiceInterface):
    """OpenStreetMap Overpass API for wheelchair accessibility data."""

    def __init__(
        self,
        settings: Settings,
        resilience: Optional[ResilienceManager] = None,
    ):
        self._timeout = settings.tool_timeout_seconds
        self._resilience = resilience

    async def enrich_accessibility(
        self,
        place_name: str,
        place_id: Optional[str] = None,
        location: Optional[str] = None,
        language: str = "es",
    ) -> AccessibilityInfo:
        if self._resilience:
            await self._resilience.pre_request("overpass", "overpass_query")

        lat, lng = self._resolve_coordinates(location)
        query = _QUERY_TEMPLATE.format(lat=lat, lng=lng)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    _OVERPASS_URL,
                    data={"data": query},
                )
                resp.raise_for_status()
                data = resp.json()

            if self._resilience:
                self._resilience.record_success("overpass")

            return self._parse_accessibility(data, place_name)

        except Exception as exc:
            if self._resilience:
                self._resilience.record_failure("overpass")
            logger.warning("overpass_query_failed", error=str(exc))
            raise

    def is_service_available(self) -> bool:
        # Overpass is public, no API key required
        return True

    def get_service_info(self) -> dict:
        return {
            "provider": "overpass_osm",
            "available": True,
            "api_key_required": False,
        }

    @staticmethod
    def _resolve_coordinates(location: Optional[str]) -> tuple[float, float]:
        """Placeholder: returns Madrid city center.

        In production, this would geocode the location string.
        """
        return (40.4168, -3.7038)  # Madrid center

    @staticmethod
    def _parse_accessibility(data: dict, place_name: str) -> AccessibilityInfo:
        elements = data.get("elements", [])
        if not elements:
            return AccessibilityInfo(
                accessibility_level="unknown",
                source="overpass_osm",
            )

        # Aggregate wheelchair tags from nearby nodes/ways
        wheelchair_values = []
        facilities: list[str] = []
        for el in elements:
            tags = el.get("tags", {})
            wc = tags.get("wheelchair", "")
            if wc:
                wheelchair_values.append(wc)
            if tags.get("wheelchair:description"):
                facilities.append(tags["wheelchair:description"])
            if tags.get("tactile_paving") == "yes":
                facilities.append("tactile_paving")
            if tags.get("wheelchair:toilet") == "yes":
                facilities.append("wheelchair_toilet")

        # Determine overall level from majority vote
        level = "unknown"
        if wheelchair_values:
            yes_count = sum(1 for v in wheelchair_values if v == "yes")
            limited_count = sum(1 for v in wheelchair_values if v == "limited")
            total = len(wheelchair_values)
            if yes_count > total / 2:
                level = "full"
            elif (yes_count + limited_count) > total / 2:
                level = "partial"
            else:
                level = "limited"

        score = {"full": 0.9, "partial": 0.6, "limited": 0.3, "unknown": 0.0}

        return AccessibilityInfo(
            accessibility_level=level,
            facilities=list(set(facilities)),
            accessibility_score=score.get(level, 0.0),
            wheelchair_accessible_entrance=level in ("full", "partial") or None,
            source="overpass_osm",
        )
