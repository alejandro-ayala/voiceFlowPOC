"""Local fallback places service using existing VENUE_DB mock data."""

from typing import Optional

import structlog

from business.domains.tourism.data.venue_data import DEFAULT_VENUE, VENUE_DB
from shared.interfaces.places_interface import PlacesServiceInterface
from shared.models.tool_models import PlaceCandidate, VenueDetail

logger = structlog.get_logger(__name__)


class LocalPlacesService(PlacesServiceInterface):
    """Fallback implementation that uses local VENUE_DB data."""

    async def text_search(
        self,
        query: str,
        location: Optional[str] = None,
        type_filter: Optional[str] = None,
        language: str = "es",
        max_results: int = 5,
    ) -> list[PlaceCandidate]:
        query_lower = query.lower()
        candidates = []
        for venue_name in VENUE_DB:
            if any(word in venue_name.lower() for word in query_lower.split()):
                candidates.append(
                    PlaceCandidate(
                        name=venue_name,
                        place_type=self._infer_type(venue_name),
                        destination=location or "Madrid",
                        source="local_db",
                    )
                )
        if not candidates:
            candidates.append(
                PlaceCandidate(
                    name=query,
                    place_type="tourism",
                    destination=location or "Madrid",
                    source="local_db",
                )
            )
        return candidates[:max_results]

    async def place_details(
        self,
        place_id: str,
        fields: Optional[list[str]] = None,
        language: str = "es",
    ) -> VenueDetail:
        data = VENUE_DB.get(place_id, DEFAULT_VENUE)
        return VenueDetail(
            name=place_id,
            venue_type=self._infer_type(place_id),
            opening_hours=data.get("opening_hours"),
            pricing=data.get("pricing"),
            accessibility_reviews=data.get("accessibility_reviews"),
            accessibility_services=data.get("accessibility_services", []),
            contact=data.get("contact"),
            source="local_db",
        )

    def is_service_available(self) -> bool:
        return True

    def get_service_info(self) -> dict:
        return {
            "provider": "local_db",
            "available": True,
            "venues_count": len(VENUE_DB),
        }

    @staticmethod
    def _infer_type(name: str) -> str:
        name_lower = name.lower()
        if "museo" in name_lower:
            return "museum"
        if "restaurante" in name_lower:
            return "restaurant"
        if "parque" in name_lower:
            return "park"
        if "musical" in name_lower or "concierto" in name_lower:
            return "entertainment"
        return "tourism"
