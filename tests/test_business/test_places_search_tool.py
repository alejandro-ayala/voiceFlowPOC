"""Tests for PlacesSearchTool with mocked service."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from business.domains.tourism.tools.places_search_tool import PlacesSearchTool
from shared.models.nlu_models import NLUEntitySet, NLUResult
from shared.models.tool_models import PlaceCandidate, ToolPipelineContext, VenueDetail


class TestPlacesSearchTool:
    @pytest.mark.asyncio
    async def test_execute_populates_place_and_venue(self):
        mock_service = MagicMock()
        mock_service.text_search = AsyncMock(
            return_value=[
                PlaceCandidate(
                    name="Museo del Prado",
                    place_id="abc123",
                    source="google_places",
                )
            ]
        )
        mock_service.place_details = AsyncMock(
            return_value=VenueDetail(
                name="Museo del Prado",
                venue_type="museum",
                source="google_places",
            )
        )
        mock_service.get_service_info = MagicMock(return_value={"provider": "google_places"})

        tool = PlacesSearchTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="Museo del Prado",
            place=PlaceCandidate(name="Museo del Prado", destination="Madrid"),
        )

        result = await tool.execute(ctx)

        assert result.place.name == "Museo del Prado"
        assert result.place.place_id == "abc123"
        assert result.venue_detail is not None
        assert result.venue_detail.venue_type == "museum"
        assert "venue info" in result.raw_tool_results

    @pytest.mark.asyncio
    async def test_execute_records_error_on_failure(self):
        mock_service = MagicMock()
        mock_service.text_search = AsyncMock(side_effect=Exception("API down"))
        mock_service.get_service_info = MagicMock(return_value={"provider": "test"})

        tool = PlacesSearchTool(mock_service)
        ctx = ToolPipelineContext(user_input="test query")

        result = await tool.execute(ctx)

        assert len(result.errors) == 1
        assert "API down" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_execute_no_place_id_skips_details(self):
        mock_service = MagicMock()
        mock_service.text_search = AsyncMock(return_value=[PlaceCandidate(name="Test Place", source="local_db")])
        mock_service.place_details = AsyncMock()
        mock_service.get_service_info = MagicMock(return_value={"provider": "local"})

        tool = PlacesSearchTool(mock_service)
        ctx = ToolPipelineContext(user_input="Test Place")

        result = await tool.execute(ctx)

        assert result.place.name == "Test Place"
        mock_service.place_details.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_uses_intent_policy_for_restaurant(self):
        mock_service = MagicMock()
        mock_service.text_search = AsyncMock(return_value=[PlaceCandidate(name="Casa Pepe", place_type="restaurant")])
        mock_service.place_details = AsyncMock()
        mock_service.get_service_info = MagicMock(return_value={"provider": "google_places"})

        tool = PlacesSearchTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="restaurantes en almería",
            nlu_result=NLUResult(
                intent="restaurant_search",
                entities=NLUEntitySet(destination="Almería"),
            ),
            place=PlaceCandidate(name="Almería", destination="Almería"),
        )

        await tool.execute(ctx)

        call_kwargs = mock_service.text_search.await_args.kwargs
        assert call_kwargs["type_filter"] == "restaurant"
        assert call_kwargs["location"] is None
        assert "restaurante accesible" in call_kwargs["query"].lower()

    @pytest.mark.asyncio
    async def test_execute_dedupes_query_tokens(self):
        mock_service = MagicMock()
        mock_service.text_search = AsyncMock(return_value=[PlaceCandidate(name="Almería", source="local_db")])
        mock_service.place_details = AsyncMock()
        mock_service.get_service_info = MagicMock(return_value={"provider": "local_db"})

        tool = PlacesSearchTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="Almería Almería restaurantes Almería",
            nlu_result=NLUResult(
                intent="restaurant_search",
                entities=NLUEntitySet(destination="Almería"),
            ),
        )

        await tool.execute(ctx)

        call_kwargs = mock_service.text_search.await_args.kwargs
        assert "almería almería" not in call_kwargs["query"].lower()

    @pytest.mark.asyncio
    async def test_execute_ranks_candidates_by_intent_type(self):
        mock_service = MagicMock()
        mock_service.text_search = AsyncMock(
            return_value=[
                PlaceCandidate(name="Museo del Prado", place_type="museum", rating=4.8, source="google_places"),
                PlaceCandidate(name="Restaurante Sol", place_type="restaurant", rating=4.1, source="google_places"),
            ]
        )
        mock_service.place_details = AsyncMock()
        mock_service.get_service_info = MagicMock(return_value={"provider": "google_places"})

        tool = PlacesSearchTool(mock_service)
        ctx = ToolPipelineContext(
            user_input="restaurantes en madrid",
            nlu_result=NLUResult(
                intent="restaurant_search",
                entities=NLUEntitySet(destination="Madrid"),
            ),
        )

        result = await tool.execute(ctx)

        assert result.place is not None
        assert result.place.name == "Restaurante Sol"
        venue_info = json.loads(result.raw_tool_results["venue info"])
        assert venue_info[0]["name"] == "Restaurante Sol"
