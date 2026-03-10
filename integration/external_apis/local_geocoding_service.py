"""Local geocoding fallback using a static Madrid venue/landmark lookup table."""

from typing import Optional

import structlog

from shared.interfaces.geocoding_interface import GeocodingServiceInterface
from shared.models.tool_models import GeocodedLocation

logger = structlog.get_logger(__name__)

# Static lat/lng for well-known Madrid landmarks (WGS-84)
_VENUE_COORDS: dict[str, tuple[float, float]] = {
    "museo del prado": (40.4138, -3.6921),
    "prado": (40.4138, -3.6921),
    "museo reina sofia": (40.4084, -3.6944),
    "reina sofia": (40.4084, -3.6944),
    "museo reina sofía": (40.4084, -3.6944),
    "parque del retiro": (40.4153, -3.6844),
    "retiro": (40.4153, -3.6844),
    "puerta del sol": (40.4169, -3.7035),
    "sol": (40.4169, -3.7035),
    "palacio real": (40.4180, -3.7143),
    "gran via": (40.4200, -3.7056),
    "gran vía": (40.4200, -3.7056),
    "plaza mayor": (40.4153, -3.7074),
    "estadio bernabeu": (40.4531, -3.6883),
    "estadio santiago bernabeu": (40.4531, -3.6883),
    "bernabeu": (40.4531, -3.6883),
    "aeropuerto adolfo suarez": (40.4936, -3.5668),
    "aeropuerto barajas": (40.4936, -3.5668),
    "barajas": (40.4936, -3.5668),
    "teatro real": (40.4183, -3.7088),
    "cibeles": (40.4193, -3.6935),
    "neptuno": (40.4143, -3.6945),
    "atocha": (40.4066, -3.6894),
    "estacion atocha": (40.4066, -3.6894),
    "madrid": (40.4168, -3.7038),
    "madrid centro": (40.4168, -3.7038),
    "centro madrid": (40.4168, -3.7038),
}

_DEFAULT_COORDS = (40.4168, -3.7038)  # Madrid city center


class LocalGeocodingService(GeocodingServiceInterface):
    """Static lookup geocoder for local/test environments.

    Searches normalised venue names, falls back to Madrid city center.
    Always reports is_service_available() = True.
    """

    async def geocode(
        self,
        address: str,
        language: str = "es",
        bias_location: Optional[tuple[float, float]] = None,
    ) -> list[GeocodedLocation]:
        key = address.lower().strip()

        # Exact match first
        if key in _VENUE_COORDS:
            lat, lng = _VENUE_COORDS[key]
            return [self._build(lat, lng, address, confidence=1.0)]

        # Partial-word match
        for venue_key, (lat, lng) in _VENUE_COORDS.items():
            if venue_key in key or key in venue_key:
                return [self._build(lat, lng, address, confidence=0.8)]

        # Token-level match (any word of the query found in a venue key)
        tokens = [t for t in key.split() if len(t) > 3]
        for token in tokens:
            for venue_key, (lat, lng) in _VENUE_COORDS.items():
                if token in venue_key:
                    return [self._build(lat, lng, address, confidence=0.5)]

        # Fallback: Madrid center
        lat, lng = _DEFAULT_COORDS
        logger.debug("local_geocoding_fallback", address=address)
        return [self._build(lat, lng, "Madrid, España", confidence=0.1)]

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        language: str = "es",
    ) -> GeocodedLocation:
        # Find nearest known venue (Euclidean approximation — fine for a city-scale fallback)
        best_key, best_dist = "madrid", float("inf")
        for venue_key, (vlat, vlng) in _VENUE_COORDS.items():
            dist = (vlat - latitude) ** 2 + (vlng - longitude) ** 2
            if dist < best_dist:
                best_dist = dist
                best_key = venue_key

        lat, lng = _VENUE_COORDS.get(best_key, _DEFAULT_COORDS)
        return self._build(lat, lng, best_key.title(), confidence=0.6)

    def is_service_available(self) -> bool:
        return True

    def get_service_info(self) -> dict:
        return {
            "provider": "local_geocoding",
            "available": True,
            "venues_count": len(_VENUE_COORDS),
        }

    @staticmethod
    def _build(lat: float, lng: float, name: str, confidence: float) -> GeocodedLocation:
        return GeocodedLocation(
            latitude=lat,
            longitude=lng,
            formatted_address=name,
            place_name=name,
            confidence=confidence,
            source="local_geocoding",
        )
