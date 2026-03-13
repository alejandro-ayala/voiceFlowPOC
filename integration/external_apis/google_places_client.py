"""Google Places API (New) client for place search and detail retrieval."""

from typing import Optional

import httpx
import structlog

from integration.configuration.settings import Settings
from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.places_interface import PlacesServiceInterface
from shared.models.tool_models import PlaceCandidate, VenueDetail

logger = structlog.get_logger(__name__)

# Google Places API (New) base URL
_BASE_URL = "https://places.googleapis.com/v1"

# Field masks for API requests
_SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.rating,places.types,"
    "places.accessibilityOptions,places.websiteUri"
)
_DETAILS_FIELD_MASK = (
    "id,displayName,formattedAddress,location,rating,types,"
    "regularOpeningHours,accessibilityOptions,"
    "currentOpeningHours,priceLevel"
)


class GooglePlacesService(PlacesServiceInterface):
    """Google Places API (New) implementation for place search and details."""

    def __init__(
        self,
        settings: Settings,
        resilience: Optional[ResilienceManager] = None,
    ):
        self._api_key = settings.google_api_key or ""
        self._timeout = settings.tool_timeout_seconds
        self._resilience = resilience

    async def text_search(
        self,
        query: str,
        location: Optional[str] = None,
        type_filter: Optional[str] = None,
        language: str = "es",
        max_results: int = 5,
    ) -> list[PlaceCandidate]:
        if self._resilience:
            await self._resilience.pre_request("google_places", "google_places_search")

        body: dict = {
            "textQuery": f"{query} {location or ''}".strip(),
            "languageCode": language,
            "maxResultCount": max_results,
        }
        if type_filter:
            body["includedType"] = type_filter

        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _SEARCH_FIELD_MASK,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{_BASE_URL}/places:searchText",
                    json=body,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            if self._resilience:
                self._resilience.record_success("google_places")

            return [self._parse_candidate(p) for p in data.get("places", [])]

        except Exception as exc:
            if self._resilience:
                self._resilience.record_failure("google_places")
            logger.warning("google_places_search_failed", error=str(exc))
            raise

    async def place_details(
        self,
        place_id: str,
        fields: Optional[list[str]] = None,
        language: str = "es",
    ) -> VenueDetail:
        if self._resilience:
            await self._resilience.pre_request("google_places", "google_places_details")

        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _DETAILS_FIELD_MASK,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{_BASE_URL}/places/{place_id}",
                    headers=headers,
                    params={"languageCode": language},
                )
                resp.raise_for_status()
                data = resp.json()

            if self._resilience:
                self._resilience.record_success("google_places")

            return self._parse_venue_detail(data)

        except Exception as exc:
            if self._resilience:
                self._resilience.record_failure("google_places")
            logger.warning("google_places_details_failed", error=str(exc))
            raise

    def is_service_available(self) -> bool:
        return bool(self._api_key)

    def get_service_info(self) -> dict:
        return {
            "provider": "google_places",
            "available": self.is_service_available(),
            "api_version": "v1 (New)",
        }

    @staticmethod
    def _parse_candidate(place: dict) -> PlaceCandidate:
        loc = place.get("location", {})
        display = place.get("displayName", {})
        return PlaceCandidate(
            name=display.get("text", "unknown"),
            place_id=place.get("id"),
            address=place.get("formattedAddress"),
            location_lat=loc.get("latitude"),
            location_lng=loc.get("longitude"),
            rating=place.get("rating"),
            types=place.get("types", []),
            website_url=place.get("websiteUri"),
            source="google_places",
        )

    @staticmethod
    def _parse_venue_detail(data: dict) -> VenueDetail:
        display = data.get("displayName", {})
        accessibility = data.get("accessibilityOptions", {})
        hours = data.get("regularOpeningHours") or data.get("currentOpeningHours")
        types = data.get("types", [])
        venue_type = types[0] if types else None

        return VenueDetail(
            name=display.get("text", "unknown"),
            venue_type=venue_type,
            opening_hours=hours,
            accessibility_reviews={"accessibility_options": accessibility},
            accessibility_services=[k for k, v in accessibility.items() if v is True],
            source="google_places",
        )
