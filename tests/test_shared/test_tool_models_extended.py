"""Tests for Phase 1 extended fields on tool models (backward compatibility)."""

from shared.models.tool_models import AccessibilityInfo, PlaceCandidate, RouteOption


class TestPlaceCandidateExtended:
    def test_new_fields_default_to_none(self):
        pc = PlaceCandidate(name="Test")
        assert pc.place_id is None
        assert pc.address is None
        assert pc.location_lat is None
        assert pc.location_lng is None
        assert pc.rating is None
        assert pc.types == []

    def test_all_fields_populated(self):
        pc = PlaceCandidate(
            name="Museo del Prado",
            place_id="abc",
            address="C/ Ruiz 23",
            location_lat=40.41,
            location_lng=-3.69,
            rating=4.7,
            types=["museum", "tourist_attraction"],
            source="google_places",
        )
        assert pc.place_id == "abc"
        assert pc.rating == 4.7
        assert len(pc.types) == 2


class TestAccessibilityInfoExtended:
    def test_wheelchair_fields_default_to_none(self):
        ai = AccessibilityInfo()
        assert ai.wheelchair_accessible_entrance is None
        assert ai.wheelchair_accessible_parking is None
        assert ai.wheelchair_accessible_restroom is None
        assert ai.wheelchair_accessible_seating is None

    def test_wheelchair_fields_populated(self):
        ai = AccessibilityInfo(
            wheelchair_accessible_entrance=True,
            wheelchair_accessible_parking=False,
            wheelchair_accessible_restroom=True,
            wheelchair_accessible_seating=None,
        )
        assert ai.wheelchair_accessible_entrance is True
        assert ai.wheelchair_accessible_parking is False


class TestRouteOptionExtended:
    def test_new_fields_default(self):
        ro = RouteOption(transport_type="walking")
        assert ro.distance_meters is None
        assert ro.steps == []

    def test_steps_populated(self):
        ro = RouteOption(
            transport_type="transit",
            distance_meters=1200,
            steps=[{"instruction": "Walk north"}],
        )
        assert ro.distance_meters == 1200
        assert len(ro.steps) == 1
