"""Tests for geocoding providers: LocalGeocodingService, NominatimGeocodingService, CachedGeocodingService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from integration.external_apis.cached_geocoding_service import CachedGeocodingService
from integration.external_apis.local_geocoding_service import LocalGeocodingService
from integration.external_apis.nominatim_client import NominatimGeocodingService
from shared.models.tool_models import GeocodedLocation


# ─── LocalGeocodingService ────────────────────────────────────────────────────

class TestLocalGeocodingService:
    @pytest.fixture
    def svc(self):
        return LocalGeocodingService()

    @pytest.mark.asyncio
    async def test_exact_match(self, svc):
        results = await svc.geocode("museo del prado")
        assert len(results) == 1
        assert abs(results[0].latitude - 40.4138) < 0.001
        assert results[0].confidence == 1.0
        assert results[0].source == "local_geocoding"

    @pytest.mark.asyncio
    async def test_partial_match(self, svc):
        results = await svc.geocode("prado")
        assert results[0].latitude == pytest.approx(40.4138, abs=0.001)

    @pytest.mark.asyncio
    async def test_token_match(self, svc):
        results = await svc.geocode("visitar el retiro")
        assert results[0].latitude == pytest.approx(40.4153, abs=0.001)

    @pytest.mark.asyncio
    async def test_unknown_falls_back_to_madrid(self, svc):
        results = await svc.geocode("lugar completamente desconocido xyz")
        assert results[0].latitude == pytest.approx(40.4168, abs=0.001)
        assert results[0].confidence < 0.5

    @pytest.mark.asyncio
    async def test_reverse_geocode_returns_nearest(self, svc):
        # Coordinates very close to Museo del Prado
        result = await svc.reverse_geocode(40.414, -3.692)
        assert isinstance(result, GeocodedLocation)
        assert result.source == "local_geocoding"

    def test_is_available(self, svc):
        assert svc.is_service_available() is True

    def test_service_info(self, svc):
        info = svc.get_service_info()
        assert info["provider"] == "local_geocoding"
        assert info["venues_count"] > 0


# ─── NominatimGeocodingService ────────────────────────────────────────────────

class TestNominatimGeocodingService:
    @pytest.fixture
    def svc(self):
        return NominatimGeocodingService(timeout=5.0)

    @pytest.mark.asyncio
    async def test_geocode_parses_response(self, svc):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {
                "lat": "40.4138",
                "lon": "-3.6921",
                "display_name": "Museo del Prado, Madrid, España",
                "name": "Museo del Prado",
                "osm_id": 12345,
                "importance": 0.85,
            }
        ]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            results = await svc.geocode("Museo del Prado")

        assert len(results) == 1
        assert results[0].latitude == pytest.approx(40.4138)
        assert results[0].longitude == pytest.approx(-3.6921)
        assert results[0].place_name == "Museo del Prado"
        assert results[0].confidence == pytest.approx(0.85)
        assert results[0].source == "nominatim"

    @pytest.mark.asyncio
    async def test_reverse_geocode_parses_response(self, svc):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "display_name": "Museo del Prado, Calle Ruiz de Alarcón, Madrid",
            "name": "Museo del Prado",
            "osm_id": 12345,
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await svc.reverse_geocode(40.4138, -3.6921)

        assert result.latitude == pytest.approx(40.4138)
        assert result.source == "nominatim"

    @pytest.mark.asyncio
    async def test_geocode_records_resilience_failure(self, svc):
        resilience = MagicMock()
        resilience.pre_request = AsyncMock()
        resilience.record_failure = MagicMock()
        svc._resilience = resilience

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("connection refused")

            with pytest.raises(Exception):
                await svc.geocode("anywhere")

        resilience.record_failure.assert_called_once_with("nominatim")

    def test_is_available(self, svc):
        assert svc.is_service_available() is True

    def test_service_info(self, svc):
        info = svc.get_service_info()
        assert info["provider"] == "nominatim"
        assert "rate_limit" in info


# ─── CachedGeocodingService ───────────────────────────────────────────────────

class TestCachedGeocodingService:
    @pytest.fixture
    def delegate(self):
        mock = MagicMock()
        mock.geocode = AsyncMock(
            return_value=[
                GeocodedLocation(
                    latitude=40.4138, longitude=-3.6921,
                    formatted_address="Museo del Prado", source="nominatim"
                )
            ]
        )
        mock.reverse_geocode = AsyncMock(
            return_value=GeocodedLocation(
                latitude=40.4138, longitude=-3.6921,
                formatted_address="Museo del Prado", source="nominatim"
            )
        )
        mock.is_service_available.return_value = True
        mock.get_service_info.return_value = {"provider": "nominatim"}
        return mock

    @pytest.fixture
    def cached(self, delegate):
        return CachedGeocodingService(delegate, ttl_seconds=60)

    @pytest.mark.asyncio
    async def test_first_call_hits_delegate(self, cached, delegate):
        await cached.geocode("Museo del Prado")
        delegate.geocode.assert_called_once()

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self, cached, delegate):
        await cached.geocode("Museo del Prado")
        await cached.geocode("Museo del Prado")
        assert delegate.geocode.call_count == 1  # second call served from cache

    @pytest.mark.asyncio
    async def test_different_language_bypasses_cache(self, cached, delegate):
        await cached.geocode("Museo del Prado", language="es")
        await cached.geocode("Museo del Prado", language="en")
        assert delegate.geocode.call_count == 2

    @pytest.mark.asyncio
    async def test_reverse_geocode_cache(self, cached, delegate):
        await cached.reverse_geocode(40.4138, -3.6921)
        await cached.reverse_geocode(40.4138, -3.6921)
        assert delegate.reverse_geocode.call_count == 1

    def test_clear_cache(self, cached, delegate):
        # Pre-populate caches manually
        cached._geocode_cache["key"] = (9999999, [])
        cached._reverse_cache["key"] = (9999999, MagicMock())
        cached.clear_cache()
        assert len(cached._geocode_cache) == 0
        assert len(cached._reverse_cache) == 0

    def test_service_info_includes_cache_stats(self, cached):
        info = cached.get_service_info()
        assert "cache" in info
        assert "ttl_seconds" in info["cache"]
