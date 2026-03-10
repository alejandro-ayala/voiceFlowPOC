"""TTL cache decorator for any GeocodingServiceInterface implementation.

Addresses Nominatim's 1 req/s rate limit: identical queries are served from
cache and never hit the network until the TTL expires.
"""

import time
from typing import Optional

import structlog

from shared.interfaces.geocoding_interface import GeocodingServiceInterface
from shared.models.tool_models import GeocodedLocation

logger = structlog.get_logger(__name__)


class CachedGeocodingService(GeocodingServiceInterface):
    """Transparent TTL cache layered over any GeocodingServiceInterface.

    Cache key: (normalised_address, language) for geocode calls.
               (rounded_lat, rounded_lng, language) for reverse calls.

    Thread safety: single-threaded async — no locking needed.
    """

    def __init__(
        self,
        delegate: GeocodingServiceInterface,
        ttl_seconds: int = 3600,
    ):
        self._delegate = delegate
        self._ttl = ttl_seconds
        # {cache_key: (expires_at, result)}
        self._geocode_cache: dict[str, tuple[float, list[GeocodedLocation]]] = {}
        self._reverse_cache: dict[str, tuple[float, GeocodedLocation]] = {}

    async def geocode(
        self,
        address: str,
        language: str = "es",
        bias_location: Optional[tuple[float, float]] = None,
    ) -> list[GeocodedLocation]:
        key = f"{address.lower().strip()}|{language}"
        now = time.monotonic()

        if key in self._geocode_cache:
            expires_at, cached = self._geocode_cache[key]
            if now < expires_at:
                logger.debug("geocoding_cache_hit", address=address)
                return cached

        result = await self._delegate.geocode(address, language=language, bias_location=bias_location)
        self._geocode_cache[key] = (now + self._ttl, result)
        return result

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        language: str = "es",
    ) -> GeocodedLocation:
        # Round to 4 decimal places (~11m precision) — enough for caching
        lat_r = round(latitude, 4)
        lng_r = round(longitude, 4)
        key = f"{lat_r}|{lng_r}|{language}"
        now = time.monotonic()

        if key in self._reverse_cache:
            expires_at, cached = self._reverse_cache[key]
            if now < expires_at:
                logger.debug("reverse_geocoding_cache_hit", lat=lat_r, lng=lng_r)
                return cached

        result = await self._delegate.reverse_geocode(latitude, longitude, language=language)
        self._reverse_cache[key] = (now + self._ttl, result)
        return result

    def is_service_available(self) -> bool:
        return self._delegate.is_service_available()

    def get_service_info(self) -> dict:
        info = self._delegate.get_service_info()
        info["cache"] = {"ttl_seconds": self._ttl, "entries": len(self._geocode_cache)}
        return info

    def clear_cache(self) -> None:
        """Evict all cached entries (useful in tests)."""
        self._geocode_cache.clear()
        self._reverse_cache.clear()
