"""Nominatim (OpenStreetMap) geocoding client.

Rate limit: 1 request/second per Nominatim usage policy.
Wrap with CachedGeocodingService to stay within limits in production.
"""

from typing import Optional

import httpx
import structlog

from integration.external_apis.resilience import ResilienceManager
from shared.interfaces.geocoding_interface import GeocodingServiceInterface
from shared.models.tool_models import GeocodedLocation

logger = structlog.get_logger(__name__)

_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
_USER_AGENT = "VoiceFlow-POC/1.0 (accessible-tourism-assistant)"


class NominatimGeocodingService(GeocodingServiceInterface):
    """OpenStreetMap Nominatim geocoding — free, no API key required.

    Important: Nominatim enforces a strict 1 req/s rate limit.
    Always deploy behind CachedGeocodingService to respect this policy.
    """

    def __init__(
        self,
        timeout: float = 5.0,
        resilience: Optional[ResilienceManager] = None,
        country_codes: str = "es",
    ):
        self._timeout = timeout
        self._resilience = resilience
        self._country_codes = country_codes  # Bias results to Spain by default

    async def geocode(
        self,
        address: str,
        language: str = "es",
        bias_location: Optional[tuple[float, float]] = None,
    ) -> list[GeocodedLocation]:
        if self._resilience:
            await self._resilience.pre_request("nominatim", "nominatim_geocode")

        params: dict = {
            "q": address,
            "format": "json",
            "limit": 5,
            "accept-language": language,
            "addressdetails": 1,
        }
        if self._country_codes:
            params["countrycodes"] = self._country_codes
        if bias_location:
            lat, lng = bias_location
            # viewbox biases (not restricts) results to this bounding box
            delta = 0.5
            params["viewbox"] = f"{lng - delta},{lat + delta},{lng + delta},{lat - delta}"
            params["bounded"] = 0  # Allow results outside viewbox as fallback

        headers = {"User-Agent": _USER_AGENT, "Accept-Language": language}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(_SEARCH_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            if self._resilience:
                self._resilience.record_success("nominatim")

            results = [self._parse_search_result(item) for item in data if isinstance(item, dict)]
            logger.info("nominatim_geocode_ok", address=address, results=len(results))
            return results

        except Exception as exc:
            if self._resilience:
                self._resilience.record_failure("nominatim")
            logger.warning("nominatim_geocode_failed", address=address, error=str(exc))
            raise

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        language: str = "es",
    ) -> GeocodedLocation:
        if self._resilience:
            await self._resilience.pre_request("nominatim", "nominatim_reverse")

        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "accept-language": language,
            "addressdetails": 1,
        }
        headers = {"User-Agent": _USER_AGENT, "Accept-Language": language}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(_REVERSE_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            if self._resilience:
                self._resilience.record_success("nominatim")

            result = self._parse_reverse_result(data, latitude, longitude)
            logger.info("nominatim_reverse_ok", lat=latitude, lng=longitude)
            return result

        except Exception as exc:
            if self._resilience:
                self._resilience.record_failure("nominatim")
            logger.warning("nominatim_reverse_failed", lat=latitude, lng=longitude, error=str(exc))
            raise

    def is_service_available(self) -> bool:
        # Nominatim is public — always available (subject to rate limits)
        return True

    def get_service_info(self) -> dict:
        return {
            "provider": "nominatim",
            "available": True,
            "api_key_required": False,
            "rate_limit": "1 req/s (use CachedGeocodingService)",
            "country_bias": self._country_codes,
        }

    @staticmethod
    def _parse_search_result(item: dict) -> GeocodedLocation:
        importance = float(item.get("importance", 0.5))
        return GeocodedLocation(
            latitude=float(item.get("lat", 0.0)),
            longitude=float(item.get("lon", 0.0)),
            formatted_address=item.get("display_name", ""),
            place_name=item.get("name") or item.get("display_name", "").split(",")[0],
            place_id=str(item.get("osm_id")) if item.get("osm_id") else None,
            confidence=min(importance, 1.0),
            source="nominatim",
        )

    @staticmethod
    def _parse_reverse_result(data: dict, lat: float, lng: float) -> GeocodedLocation:
        return GeocodedLocation(
            latitude=lat,
            longitude=lng,
            formatted_address=data.get("display_name", ""),
            place_name=data.get("name") or data.get("display_name", "").split(",")[0],
            place_id=str(data.get("osm_id")) if data.get("osm_id") else None,
            confidence=1.0,
            source="nominatim",
        )
