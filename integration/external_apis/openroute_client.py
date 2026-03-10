"""OpenRouteService client for wheelchair-accessible walking directions."""

from typing import Optional

import httpx
import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.directions_interface import DirectionsServiceInterface
from shared.interfaces.geocoding_interface import GeocodingServiceInterface
from shared.models.tool_models import RouteOption

logger = structlog.get_logger(__name__)

_BASE_URL = "https://api.openrouteservice.org/v2/directions"
_MADRID_CENTER = [-3.7038, 40.4168]  # [lng, lat] — ORS coordinate order


class OpenRouteDirectionsService(DirectionsServiceInterface):
    """OpenRouteService implementation for wheelchair/walking directions."""

    def __init__(
        self,
        settings: Settings,
        resilience: Optional[ResilienceManager] = None,
        geocoding_service: Optional[GeocodingServiceInterface] = None,
    ):
        self._api_key = settings.openroute_api_key or ""
        self._timeout = settings.tool_timeout_seconds
        self._resilience = resilience
        self._geocoding = geocoding_service

    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
        accessibility_profile: Optional[str] = None,
        language: str = "es",
    ) -> list[RouteOption]:
        if self._resilience:
            await self._resilience.pre_request("openroute", "openroute_directions")

        profile = self._select_profile(mode, accessibility_profile)

        origin_coords = await self._resolve_coords(origin, language)
        destination_coords = await self._resolve_coords(destination, language)

        body: dict = {
            "coordinates": [origin_coords, destination_coords],
            "language": language,
            "instructions": True,
        }

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = self._api_key

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{_BASE_URL}/{profile}/json",
                    json=body,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            if self._resilience:
                self._resilience.record_success("openroute")

            return self._parse_routes(data, mode)

        except Exception as exc:
            if self._resilience:
                self._resilience.record_failure("openroute")
            logger.warning("openroute_directions_failed", error=str(exc))
            raise

    async def _resolve_coords(self, address: str, language: str) -> list[float]:
        """Resolve an address string to [lng, lat] using the injected geocoding service.

        Falls back to Madrid city center when geocoding is unavailable or returns
        no results, preserving the original graceful-degradation behaviour.
        """
        if self._geocoding:
            try:
                candidates = await self._geocoding.geocode(address, language=language)
                if candidates:
                    loc = candidates[0]
                    logger.debug(
                        "openroute_coords_resolved",
                        address=address,
                        lat=loc.latitude,
                        lng=loc.longitude,
                        confidence=loc.confidence,
                        source=loc.source,
                    )
                    return [loc.longitude, loc.latitude]  # ORS expects [lng, lat]
            except Exception as exc:
                logger.warning("openroute_geocoding_failed", address=address, error=str(exc))

        logger.debug("openroute_coords_fallback", address=address)
        return _MADRID_CENTER

    def is_service_available(self) -> bool:
        # OpenRouteService has a free tier without key (lower limits)
        return True

    def get_service_info(self) -> dict:
        return {
            "provider": "openrouteservice",
            "available": True,
            "has_api_key": bool(self._api_key),
            "geocoding": self._geocoding.get_service_info().get("provider") if self._geocoding else None,
        }

    @staticmethod
    def _select_profile(mode: str, accessibility_profile: Optional[str]) -> str:
        if accessibility_profile == "wheelchair":
            return "wheelchair"
        mapping = {
            "walking": "foot-walking",
            "cycling": "cycling-regular",
            "driving": "driving-car",
        }
        return mapping.get(mode.lower(), "foot-walking")

    @staticmethod
    def _parse_routes(data: dict, mode: str) -> list[RouteOption]:
        routes = []
        for route in data.get("routes", []):
            summary = route.get("summary", {})
            duration_sec = summary.get("duration", 0)
            distance_m = summary.get("distance", 0)

            steps = []
            for segment in route.get("segments", []):
                for step in segment.get("steps", []):
                    steps.append({"instruction": step.get("instruction", "")})

            routes.append(
                RouteOption(
                    transport_type=mode,
                    duration_minutes=max(1, int(duration_sec / 60)),
                    distance_meters=int(distance_m),
                    steps=steps,
                    source="openrouteservice",
                )
            )
        return routes
