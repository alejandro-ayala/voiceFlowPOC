"""Google Routes API client for transit directions with wheelchair preferences."""

from typing import Optional

import httpx
import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.directions_interface import DirectionsServiceInterface
from shared.models.tool_models import RouteOption

logger = structlog.get_logger(__name__)

_BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

_FIELD_MASK = (
    "routes.duration,routes.distanceMeters,routes.legs.steps.navigationInstruction,"
    "routes.legs.steps.transitDetails,routes.travelAdvisory"
)


class GoogleDirectionsService(DirectionsServiceInterface):
    """Google Routes API implementation for transit directions."""

    def __init__(
        self,
        settings: Settings,
        resilience: Optional[ResilienceManager] = None,
    ):
        self._api_key = settings.google_api_key or ""
        self._timeout = settings.tool_timeout_seconds
        self._resilience = resilience

    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
        accessibility_profile: Optional[str] = None,
        language: str = "es",
    ) -> list[RouteOption]:
        if self._resilience:
            await self._resilience.pre_request("google_directions", "google_directions")

        travel_mode = self._map_travel_mode(mode)
        body: dict = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": travel_mode,
            "languageCode": language,
            "computeAlternativeRoutes": True,
        }

        if accessibility_profile == "wheelchair" and travel_mode == "TRANSIT":
            body["transitPreferences"] = {
                "allowedTravelModes": ["BUS", "SUBWAY", "TRAIN"],
                "routingPreference": "FEWER_TRANSFERS",
            }

        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_BASE_URL, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            if self._resilience:
                self._resilience.record_success("google_directions")

            return [self._parse_route(r, mode) for r in data.get("routes", [])]

        except Exception as exc:
            if self._resilience:
                self._resilience.record_failure("google_directions")
            logger.warning("google_directions_failed", error=str(exc))
            raise

    def is_service_available(self) -> bool:
        return bool(self._api_key)

    def get_service_info(self) -> dict:
        return {
            "provider": "google_routes",
            "available": self.is_service_available(),
            "api_version": "v2",
        }

    @staticmethod
    def _map_travel_mode(mode: str) -> str:
        mapping = {
            "transit": "TRANSIT",
            "walking": "WALK",
            "driving": "DRIVE",
            "bicycling": "BICYCLE",
        }
        return mapping.get(mode.lower(), "TRANSIT")

    @staticmethod
    def _parse_route(route: dict, mode: str) -> RouteOption:
        duration_str = route.get("duration", "0s")
        seconds = int(duration_str.rstrip("s")) if duration_str.endswith("s") else 0
        duration_minutes = max(1, seconds // 60)

        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                nav = step.get("navigationInstruction", {})
                if nav.get("instructions"):
                    steps.append({"instruction": nav["instructions"]})

        return RouteOption(
            transport_type=mode,
            duration_minutes=duration_minutes,
            distance_meters=route.get("distanceMeters"),
            steps=steps,
            source="google_routes",
        )
