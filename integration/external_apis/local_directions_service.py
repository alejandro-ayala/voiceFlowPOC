"""Local fallback directions service using existing ROUTE_DB mock data."""

from typing import Optional

import structlog

from business.domains.tourism.data.route_data import DEFAULT_ROUTE, ROUTE_DB
from shared.interfaces.directions_interface import DirectionsServiceInterface
from shared.models.tool_models import RouteOption

logger = structlog.get_logger(__name__)


class LocalDirectionsService(DirectionsServiceInterface):
    """Fallback implementation that uses local ROUTE_DB data."""

    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
        accessibility_profile: Optional[str] = None,
        language: str = "es",
    ) -> list[RouteOption]:
        route_data = self._find_route(destination)
        raw_routes = route_data.get("routes", [])
        routes = []
        for r in raw_routes:
            if isinstance(r, dict):
                routes.append(
                    RouteOption(
                        transport_type=r.get("transport", "unknown"),
                        duration_minutes=self._parse_duration(r.get("duration", "")),
                        description=r.get("duration", ""),
                        steps=[{"instruction": step} for step in r.get("steps", [])],
                        source="local_db",
                    )
                )
        return routes

    def is_service_available(self) -> bool:
        return True

    def get_service_info(self) -> dict:
        return {
            "provider": "local_db",
            "available": True,
            "destinations_count": len(ROUTE_DB),
        }

    @staticmethod
    def _find_route(destination: str) -> dict:
        for key in ROUTE_DB:
            if key.lower() in destination.lower() or destination.lower() in key.lower():
                return ROUTE_DB[key]
        return DEFAULT_ROUTE

    @staticmethod
    def _parse_duration(duration_str: str) -> Optional[int]:
        import re

        match = re.search(r"(\d+)", duration_str)
        return int(match.group(1)) if match else None
