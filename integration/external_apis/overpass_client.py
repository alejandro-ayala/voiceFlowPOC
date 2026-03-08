"""Overpass API (OpenStreetMap) client for accessibility enrichment."""

import time
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
        self._debug_raw_enabled = settings.accessibility_debug_raw
        self._resilience = resilience
        self._last_debug_snapshot: Optional[dict] = None

    async def enrich_accessibility(
        self,
        place_name: str,
        place_id: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        language: str = "es",
    ) -> AccessibilityInfo:
        started_at = time.perf_counter()
        if self._resilience:
            await self._resilience.pre_request("overpass", "overpass_query")

        lat, lng = self._resolve_coordinates(location, latitude, longitude)
        query = _QUERY_TEMPLATE.format(lat=lat, lng=lng)

        logger.info(
            "overpass_query_started",
            place_name=place_name,
            place_id=place_id,
            location=location,
            language=language,
            lat=lat,
            lng=lng,
            timeout_seconds=self._timeout,
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    _OVERPASS_URL,
                    data={"data": query},
                )
                resp.raise_for_status()
                data = resp.json()

            elements = data.get("elements", []) if isinstance(data, dict) else []
            duration_ms = int((time.perf_counter() - started_at) * 1000)

            self._last_debug_snapshot = {
                "provider": "overpass_osm",
                "place_name": place_name,
                "place_id": place_id,
                "location": location,
                "lat": lat,
                "lng": lng,
                "query": query,
                "response_normalized": self._normalize_response(data),
            }
            if self._debug_raw_enabled:
                self._last_debug_snapshot["response_raw"] = data

            if self._resilience:
                self._resilience.record_success("overpass")

            logger.info(
                "overpass_query_completed",
                place_name=place_name,
                place_id=place_id,
                duration_ms=duration_ms,
                elements_count=len(elements) if isinstance(elements, list) else 0,
                debug_raw_enabled=self._debug_raw_enabled,
            )

            return self._parse_accessibility(data, place_name)

        except Exception as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            if self._resilience:
                self._resilience.record_failure("overpass")
            logger.warning(
                "overpass_query_failed "
                f"place_name={place_name} place_id={place_id} location={location} "
                f"duration_ms={duration_ms} timeout_seconds={self._timeout} "
                f"error_type={type(exc).__name__} error={repr(exc)}"
            )
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

    def get_debug_snapshot(self) -> Optional[dict]:
        return self._last_debug_snapshot

    @staticmethod
    def _resolve_coordinates(
        location: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> tuple[float, float]:
        """Resolve query coordinates, prioritizing resolved place coordinates.

        Falls back to Madrid city center when coordinates are unavailable.
        """
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            return (float(latitude), float(longitude))
        return (40.4168, -3.7038)  # Madrid center

    @staticmethod
    def _normalize_response(data: dict) -> dict:
        elements = data.get("elements", []) if isinstance(data, dict) else []
        if not isinstance(elements, list):
            elements = []

        wheelchair_counts = {
            "yes": 0,
            "limited": 0,
            "no": 0,
            "unknown": 0,
        }
        sampled_elements: list[dict] = []

        for item in elements:
            if not isinstance(item, dict):
                continue
            tags = item.get("tags", {})
            if not isinstance(tags, dict):
                tags = {}

            wheelchair = str(tags.get("wheelchair", "unknown") or "unknown").lower()
            if wheelchair not in wheelchair_counts:
                wheelchair = "unknown"
            wheelchair_counts[wheelchair] += 1

            if len(sampled_elements) < 20:
                sampled_elements.append(
                    {
                        "type": item.get("type"),
                        "id": item.get("id"),
                        "name": tags.get("name"),
                        "wheelchair": tags.get("wheelchair"),
                        "wheelchair_description": tags.get("wheelchair:description"),
                        "tactile_paving": tags.get("tactile_paving"),
                        "wheelchair_toilet": tags.get("wheelchair:toilet"),
                        "amenity": tags.get("amenity"),
                        "tourism": tags.get("tourism"),
                        "highway": tags.get("highway"),
                    }
                )

        return {
            "elements_count": len(elements),
            "wheelchair_counts": wheelchair_counts,
            "sampled_elements": sampled_elements,
        }

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
