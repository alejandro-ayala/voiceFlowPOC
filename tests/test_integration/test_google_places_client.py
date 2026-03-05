"""Tests for GooglePlacesService with mocked httpx."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integration.external_apis.google_places_client import GooglePlacesService
from shared.models.tool_models import PlaceCandidate


def _make_settings(**overrides):
    settings = MagicMock()
    settings.google_api_key = overrides.get("google_api_key", "test-key")
    settings.tool_timeout_seconds = overrides.get("tool_timeout_seconds", 3.0)
    return settings


class TestGooglePlacesService:
    def test_is_available_with_key(self):
        svc = GooglePlacesService(_make_settings(google_api_key="real-key"))
        assert svc.is_service_available() is True

    def test_is_unavailable_without_key(self):
        svc = GooglePlacesService(_make_settings(google_api_key=""))
        assert svc.is_service_available() is False

    def test_service_info(self):
        svc = GooglePlacesService(_make_settings())
        info = svc.get_service_info()
        assert info["provider"] == "google_places"
        assert info["api_version"] == "v1 (New)"

    @pytest.mark.asyncio
    async def test_text_search_parses_response(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "places": [
                {
                    "id": "abc123",
                    "displayName": {"text": "Museo del Prado"},
                    "formattedAddress": "C/ Ruiz de Alarcón 23, Madrid",
                    "location": {"latitude": 40.4138, "longitude": -3.6921},
                    "rating": 4.7,
                    "types": ["museum"],
                    "accessibilityOptions": {
                        "wheelchairAccessibleEntrance": True,
                    },
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        svc = GooglePlacesService(_make_settings())

        with patch("integration.external_apis.google_places_client.httpx.AsyncClient", return_value=mock_client):
            results = await svc.text_search("Museo del Prado", location="Madrid")

        assert len(results) == 1
        assert isinstance(results[0], PlaceCandidate)
        assert results[0].name == "Museo del Prado"
        assert results[0].place_id == "abc123"
        assert results[0].rating == 4.7
        assert results[0].source == "google_places"

    @pytest.mark.asyncio
    async def test_text_search_records_failure_on_error(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))

        resilience = MagicMock()
        resilience.pre_request = AsyncMock()

        svc = GooglePlacesService(_make_settings(), resilience=resilience)

        with patch("integration.external_apis.google_places_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception, match="timeout"):
                await svc.text_search("test")

        resilience.record_failure.assert_called_once_with("google_places")
