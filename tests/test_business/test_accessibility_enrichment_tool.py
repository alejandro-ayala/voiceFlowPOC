"""Tests for AccessibilityEnrichmentTool with mocked service."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from business.domains.tourism.tools.accessibility_enrichment_tool import (
    AccessibilityEnrichmentTool,
)
from shared.models.tool_models import (
    AccessibilityInfo,
    PlaceCandidate,
    ToolPipelineContext,
)


class TestAccessibilityEnrichmentTool:
    @pytest.mark.asyncio
    async def test_execute_populates_accessibility(self):
        mock_service = MagicMock()
        mock_service.enrich_accessibility = AsyncMock(
            return_value=AccessibilityInfo(
                accessibility_level="full",
                accessibility_score=0.9,
                facilities=["ramp", "elevator"],
                wheelchair_accessible_entrance=True,
                source="overpass_osm",
            )
        )
        mock_service.get_service_info = MagicMock(return_value={"provider": "overpass"})
        mock_service.get_debug_snapshot = MagicMock(
            return_value={
                "provider": "overpass_osm",
                "response_raw": {"elements": [{"id": 1, "tags": {"wheelchair": "yes"}}]},
            }
        )

        tool = AccessibilityEnrichmentTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="accessibility info for Prado",
            place=PlaceCandidate(name="Museo del Prado", place_id="abc"),
        )

        result = await tool.execute(ctx)

        assert result.accessibility is not None
        assert result.accessibility.accessibility_level == "full"
        assert result.accessibility.wheelchair_accessible_entrance is True
        assert "accessibility" in result.raw_tool_results
        assert "accessibility_overpass_raw" in result.raw_tool_results
        assert "accessibility_comparison" in result.raw_tool_results

    @pytest.mark.asyncio
    async def test_execute_records_error_on_failure(self):
        mock_service = MagicMock()
        mock_service.enrich_accessibility = AsyncMock(side_effect=Exception("OSM down"))
        mock_service.get_service_info = MagicMock(return_value={"provider": "test"})
        mock_service.get_debug_snapshot = MagicMock(return_value={"provider": "test"})

        tool = AccessibilityEnrichmentTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="test",
            place=PlaceCandidate(name="Test Place"),
        )

        result = await tool.execute(ctx)

        assert len(result.errors) == 1
        assert "OSM down" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_execute_no_place_returns_early(self):
        mock_service = MagicMock()
        mock_service.enrich_accessibility = AsyncMock()
        mock_service.get_debug_snapshot = MagicMock(return_value=None)

        tool = AccessibilityEnrichmentTool(mock_service)
        ctx = ToolPipelineContext(user_input="hello")

        await tool.execute(ctx)

        mock_service.enrich_accessibility.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_builds_google_overpass_comparison(self):
        mock_service = MagicMock()
        mock_service.enrich_accessibility = AsyncMock(
            return_value=AccessibilityInfo(
                accessibility_level="partial",
                accessibility_score=0.6,
                wheelchair_accessible_entrance=None,
                source="overpass_osm",
            )
        )
        mock_service.get_service_info = MagicMock(return_value={"provider": "overpass_osm"})
        mock_service.get_debug_snapshot = MagicMock(
            return_value={
                "provider": "overpass_osm",
                "response_raw": {
                    "elements": [
                        {"id": 10, "tags": {"wheelchair": "yes", "tactile_paving": "yes"}},
                    ]
                },
            }
        )

        tool = AccessibilityEnrichmentTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="prado accesible",
            place=PlaceCandidate(name="Museo del Prado", place_id="abc"),
            raw_tool_results={
                "accessibility_google": json.dumps(
                    {
                        "source": "google_places",
                        "normalized": {
                            "wheelchair_accessible_entrance": True,
                            "wheelchair_accessible_parking": True,
                            "wheelchair_accessible_restroom": False,
                            "wheelchair_accessible_seating": True,
                        },
                        "accessibility_level": "partial",
                        "accessibility_score": 0.75,
                    }
                )
            },
        )

        result = await tool.execute(ctx)

        assert result.accessibility is not None
        assert result.accessibility.wheelchair_accessible_entrance is True
        assert result.accessibility.source == "overpass_osm+google_places"

        comparison = json.loads(result.raw_tool_results["accessibility_comparison"])
        assert comparison["google_available"] is True
        assert comparison["provider_has_payload"] is True
        assert "field_by_field" in comparison
