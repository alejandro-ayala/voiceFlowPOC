"""Unit tests for LocationNERTool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from business.domains.tourism.tools.location_ner_tool import LocationNERTool


class TestLocationNERTool:
    """Test suite for LocationNERTool."""

    @pytest.fixture
    def location_ner_tool(self):
        """Create a LocationNERTool instance for testing."""
        return LocationNERTool()

    def test_tool_attributes(self, location_ner_tool):
        """Test that LocationNERTool has correct attributes."""
        assert location_ner_tool.name == "location_ner"
        assert location_ner_tool.description is not None
        assert "location" in location_ner_tool.description.lower()

    def test_run_with_unavailable_service(self, location_ner_tool):
        """Test handling when NER service is unavailable."""
        with patch("business.domains.tourism.tools.location_ner_tool.NERServiceFactory") as mock_factory:
            mock_service = MagicMock()
            mock_service.is_service_available.return_value = False
            mock_factory.create_from_settings.return_value = mock_service

            result_str = location_ner_tool._run("test input")
            result = json.loads(result_str)

            assert result["status"] == "unavailable"
            assert result["locations"] == []
            assert result["top_location"] is None

    def test_run_with_valid_locations(self, location_ner_tool):
        """Test successful extraction of locations."""
        with patch("business.domains.tourism.tools.location_ner_tool.NERServiceFactory") as mock_factory:
            mock_service = AsyncMock()
            mock_service.is_service_available.return_value = True
            mock_service.extract_locations.return_value = {
                "locations": [{"name": "Palacio Real", "type": "LOC"}, {"name": "Madrid", "type": "GPE"}],
                "top_location": "Palacio Real",
                "provider": "spacy",
                "model": "es_core_news_md",
                "language": "es",
                "status": "ok",
            }
            mock_factory.create_from_settings.return_value = mock_service

            result_str = location_ner_tool._run("Quiero visitar el Palacio Real en Madrid")
            result = json.loads(result_str)

            assert result["status"] == "ok"
            assert len(result["locations"]) == 2
            assert result["top_location"] == "Palacio Real"
            assert result["provider"] == "spacy"

    def test_run_with_empty_input(self, location_ner_tool):
        """Test handling of empty input."""
        with patch("business.domains.tourism.tools.location_ner_tool.NERServiceFactory") as mock_factory:
            mock_service = AsyncMock()
            mock_service.is_service_available.return_value = True
            mock_service.extract_locations.return_value = {
                "locations": [],
                "top_location": None,
                "provider": "spacy",
                "model": "es_core_news_md",
                "language": "es",
                "status": "ok",
            }
            mock_factory.create_from_settings.return_value = mock_service

            result_str = location_ner_tool._run("")
            result = json.loads(result_str)

            assert result["status"] == "ok"
            assert result["locations"] == []
            assert result["top_location"] is None

    def test_run_with_error(self, location_ner_tool):
        """Test error handling during NER extraction."""
        with patch("business.domains.tourism.tools.location_ner_tool.NERServiceFactory") as mock_factory:
            mock_service = MagicMock()
            mock_service.is_service_available.return_value = True
            mock_service.extract_locations.side_effect = RuntimeError("Service error")
            mock_factory.create_from_settings.return_value = mock_service

            result_str = location_ner_tool._run("test input")
            result = json.loads(result_str)

            assert result["status"] == "error"
            assert result["locations"] == []
            assert "error" in result.get("reason", "").lower()

    def test_run_with_language_parameter(self, location_ner_tool):
        """Test that language parameter is passed correctly."""
        with patch("business.domains.tourism.tools.location_ner_tool.NERServiceFactory") as mock_factory:
            mock_service = AsyncMock()
            mock_service.is_service_available.return_value = True
            mock_service.extract_locations.return_value = {
                "locations": [],
                "top_location": None,
                "provider": "spacy",
                "model": "en_core_web_md",
                "language": "en",
                "status": "ok",
            }
            mock_factory.create_from_settings.return_value = mock_service

            result_str = location_ner_tool._run("London is a great city", language="en")
            result = json.loads(result_str)

            assert result["language"] == "en"
            mock_service.extract_locations.assert_called_once()

    @pytest.mark.asyncio
    async def test_arun_with_valid_locations(self, location_ner_tool):
        """Test async extraction of locations."""
        with patch("business.domains.tourism.tools.location_ner_tool.NERServiceFactory") as mock_factory:
            mock_service = AsyncMock()
            mock_service.is_service_available.return_value = True
            mock_service.extract_locations.return_value = {
                "locations": [{"name": "Palacio Real", "type": "LOC"}],
                "top_location": "Palacio Real",
                "provider": "spacy",
                "model": "es_core_news_md",
                "language": "es",
                "status": "ok",
            }
            mock_factory.create_from_settings.return_value = mock_service

            result_str = await location_ner_tool._arun("Palacio Real")
            result = json.loads(result_str)

            assert result["status"] == "ok"
            assert len(result["locations"]) == 1

    @pytest.mark.asyncio
    async def test_arun_with_unavailable_service(self, location_ner_tool):
        """Test async handling when NER service is unavailable."""
        with patch("business.domains.tourism.tools.location_ner_tool.NERServiceFactory") as mock_factory:
            mock_service = MagicMock()
            mock_service.is_service_available.return_value = False
            mock_factory.create_from_settings.return_value = mock_service

            result_str = await location_ner_tool._arun("test input")
            result = json.loads(result_str)

            assert result["status"] == "unavailable"
            assert result["locations"] == []
