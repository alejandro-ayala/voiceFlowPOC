"""Geocoding service interface: address/name → coordinates and coordinates → address."""

from abc import ABC, abstractmethod
from typing import Optional

from shared.models.tool_models import GeocodedLocation


class GeocodingServiceInterface(ABC):
    """Contract for geocoding services (Nominatim, Google Geocoding, etc.).

    A single interface covers all geocoding use cases:
      - Place name / address → coordinates  (geocode)
      - GPS coordinates → address           (reverse_geocode)

    Both operations return the same GeocodedLocation model, ensuring a uniform
    contract across the pipeline regardless of the input type.
    """

    @abstractmethod
    async def geocode(
        self,
        address: str,
        language: str = "es",
        bias_location: Optional[tuple[float, float]] = None,
    ) -> list[GeocodedLocation]:
        """Resolve a place name or address to one or more candidate locations.

        Args:
            address: Free-text address or place name (e.g. "Museo del Prado, Madrid").
            language: Preferred response language (BCP-47 code).
            bias_location: Optional (lat, lng) to prefer geographically close results.

        Returns:
            Ranked list of candidates (most confident first). Empty list when not found.
        """
        ...

    @abstractmethod
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        language: str = "es",
    ) -> GeocodedLocation:
        """Resolve GPS coordinates to a human-readable address.

        Intended for user current-location lookups: the frontend sends device GPS
        coordinates and this method returns a GeocodedLocation with the same
        contract as geocode(), keeping the pipeline uniform.

        Args:
            latitude: WGS-84 latitude.
            longitude: WGS-84 longitude.
            language: Preferred response language (BCP-47 code).

        Returns:
            Single GeocodedLocation (best match).
        """
        ...

    @abstractmethod
    def is_service_available(self) -> bool:
        """Return True if the provider is ready (e.g. API key present, local DB loaded)."""
        ...

    @abstractmethod
    def get_service_info(self) -> dict:
        """Return provider metadata: name, status, rate limits, etc."""
        ...
