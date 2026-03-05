"""Tests for DirectionsTool with mocked service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from business.domains.tourism.tools.directions_tool import DirectionsTool
from shared.models.tool_models import (
    PlaceCandidate,
    RouteOption,
    ToolPipelineContext,
)


class TestDirectionsTool:
    @pytest.mark.asyncio
    async def test_execute_populates_routes(self):
        mock_service = MagicMock()
        mock_service.get_directions = AsyncMock(
            return_value=[
                RouteOption(
                    transport_type="transit",
                    duration_minutes=15,
                    source="google_routes",
                )
            ]
        )
        mock_service.get_service_info = MagicMock(return_value={"provider": "google_routes"})

        tool = DirectionsTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="How to get to Prado",
            place=PlaceCandidate(name="Museo del Prado", address="C/ Ruiz 23"),
        )

        result = await tool.execute(ctx)

        assert len(result.routes) == 1
        assert result.routes[0].transport_type == "transit"
        assert result.routes[0].duration_minutes == 15
        assert "routes" in result.raw_tool_results

    @pytest.mark.asyncio
    async def test_execute_records_error_on_failure(self):
        mock_service = MagicMock()
        mock_service.get_directions = AsyncMock(side_effect=Exception("Timeout"))
        mock_service.get_service_info = MagicMock(return_value={"provider": "test"})

        tool = DirectionsTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="test",
            place=PlaceCandidate(name="Test"),
        )

        result = await tool.execute(ctx)

        assert len(result.errors) == 1
        assert "Timeout" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_execute_no_destination_returns_early(self):
        mock_service = MagicMock()
        mock_service.get_directions = AsyncMock()

        tool = DirectionsTool(mock_service)
        ctx = ToolPipelineContext(user_input="hello")

        result = await tool.execute(ctx)

        mock_service.get_directions.assert_not_called()
        assert len(result.routes) == 0
