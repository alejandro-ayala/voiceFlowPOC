"""Places service interface contract for place search and detail retrieval."""

from abc import ABC, abstractmethod
from typing import Optional

from shared.models.tool_models import PlaceCandidate, VenueDetail


class PlacesServiceInterface(ABC):
    """Contract for place search and detail services (Google Places, local DB, etc.)."""

    @abstractmethod
    async def text_search(
        self,
        query: str,
        location: Optional[str] = None,
        type_filter: Optional[str] = None,
        language: str = "es",
        max_results: int = 5,
    ) -> list[PlaceCandidate]:
        """Search for places by text query. Return ranked candidates."""
        ...

    @abstractmethod
    async def place_details(
        self,
        place_id: str,
        fields: Optional[list[str]] = None,
        language: str = "es",
    ) -> VenueDetail:
        """Get detailed information for a specific place."""
        ...

    @abstractmethod
    def is_service_available(self) -> bool:
        """Report if the provider is ready (API key set, etc.)."""
        ...

    @abstractmethod
    def get_service_info(self) -> dict:
        """Return provider metadata: name, status, capabilities."""
        ...
