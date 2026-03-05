"""Unit tests for inter-tool pipeline models (Phase 0 contracts)."""

import pytest

from shared.models.tool_models import (
    AccessibilityInfo,
    PlaceCandidate,
    RouteOption,
    ToolError,
    ToolPipelineContext,
    VenueDetail,
)


@pytest.mark.unit
class TestToolPipelineContext:
    def test_defaults(self):
        ctx = ToolPipelineContext(user_input="test query")
        assert ctx.user_input == "test query"
        assert ctx.language == "es"
        assert ctx.profile_context is None
        assert ctx.nlu_result is None
        assert ctx.resolved_entities is None
        assert ctx.place is None
        assert ctx.accessibility is None
        assert ctx.routes == []
        assert ctx.venue_detail is None
        assert ctx.raw_tool_results == {}
        assert ctx.errors == []

    def test_roundtrip_json(self):
        ctx = ToolPipelineContext(
            user_input="¿Cómo llego al Prado?",
            language="es",
        )
        restored = ToolPipelineContext.model_validate_json(ctx.model_dump_json())
        assert restored.user_input == ctx.user_input
        assert restored.language == ctx.language

    def test_with_nested_models(self):
        ctx = ToolPipelineContext(
            user_input="test",
            place=PlaceCandidate(name="Museo del Prado", place_type="museum"),
            accessibility=AccessibilityInfo(accessibility_level="high", accessibility_score=9.2),
            routes=[
                RouteOption(transport_type="metro", duration_minutes=15),
                RouteOption(transport_type="walking", duration_minutes=30),
            ],
            venue_detail=VenueDetail(name="Museo del Prado", venue_type="museum"),
            errors=[ToolError(source="routes", message="timeout")],
        )
        assert ctx.place.name == "Museo del Prado"
        assert ctx.accessibility.accessibility_score == pytest.approx(9.2)
        assert len(ctx.routes) == 2
        assert ctx.venue_detail.venue_type == "museum"
        assert len(ctx.errors) == 1


@pytest.mark.unit
class TestAccessibilityInfo:
    def test_defaults(self):
        info = AccessibilityInfo()
        assert info.accessibility_level == "general"
        assert info.accessibility_score == 0.0
        assert info.facilities == []
        assert info.source == "unknown"

    def test_roundtrip(self):
        info = AccessibilityInfo(
            accessibility_level="high",
            venue_rating=9.0,
            accessibility_score=8.5,
            certification="AIS",
            source="local_db",
        )
        restored = AccessibilityInfo.model_validate_json(info.model_dump_json())
        assert restored.accessibility_score == pytest.approx(8.5)
        assert restored.certification == "AIS"


@pytest.mark.unit
class TestRouteOption:
    def test_required_field(self):
        route = RouteOption(transport_type="metro")
        assert route.transport_type == "metro"
        assert route.duration_minutes is None

    def test_full_route(self):
        route = RouteOption(
            transport_type="bus",
            duration_minutes=25,
            accessibility_score=7.5,
            description="Línea 27 adaptada",
            source="google_directions",
        )
        assert route.description == "Línea 27 adaptada"


@pytest.mark.unit
class TestVenueDetail:
    def test_required_field(self):
        venue = VenueDetail(name="Retiro")
        assert venue.name == "Retiro"
        assert venue.venue_type is None

    def test_full_venue(self):
        venue = VenueDetail(
            name="Museo del Prado",
            venue_type="museum",
            opening_hours={"lunes": "10:00-20:00"},
            pricing={"general": "15€"},
            source="local_db",
        )
        assert venue.opening_hours["lunes"] == "10:00-20:00"


@pytest.mark.unit
class TestPlaceCandidate:
    def test_basic(self):
        place = PlaceCandidate(name="Retiro", place_type="park")
        assert place.name == "Retiro"
        assert place.source == "nlu"

    def test_with_destination(self):
        place = PlaceCandidate(
            name="Museo del Prado",
            destination="Madrid",
            source="google_places",
        )
        assert place.destination == "Madrid"


@pytest.mark.unit
class TestToolError:
    def test_basic(self):
        err = ToolError(source="accessibility", message="API timeout")
        assert err.source == "accessibility"
        assert err.message == "API timeout"
