"""Tests for ResponseTransformer: pipeline_context -> Recommendation[]."""

from application.orchestration.response_transformer import ResponseTransformer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_place(name="Museo del Prado", place_id="pid_1", rating=4.5, source="google_places", types=None):
    return {
        "name": name,
        "place_id": place_id,
        "rating": rating,
        "source": source,
        "types": types or ["museum"],
        "location_lat": 40.4138,
        "location_lng": -3.6921,
    }


def _make_acc(level="good", score=7.5, entrance=True, parking=False):
    return {
        "accessibility_level": level,
        "accessibility_score": score,
        "facilities": ["wheelchair_ramps"],
        "certification": None,
        "warnings": [],
        "wheelchair_accessible_entrance": entrance,
        "wheelchair_accessible_parking": parking,
        "wheelchair_accessible_restroom": None,
        "wheelchair_accessible_seating": None,
    }


def _make_route(transport="metro", duration_minutes=12, acc_score=0.9):
    return {
        "transport_type": transport,
        "duration_minutes": duration_minutes,
        "accessibility_score": acc_score,
        "estimated_cost": "1.50€",
        "steps": ["Camina 200m", "Toma la línea 1"],
    }


def _pipeline(places, acc_map=None, routes_map=None):
    return {
        "places": places,
        "accessibility_map": acc_map or {},
        "routes_map": routes_map or {},
    }


# ---------------------------------------------------------------------------
# Tests: empty / missing input
# ---------------------------------------------------------------------------


class TestTransformEdgeCases:
    def test_none_returns_empty(self):
        assert ResponseTransformer.transform(None) == []

    def test_empty_dict_returns_empty(self):
        assert ResponseTransformer.transform({}) == []

    def test_no_places_returns_empty(self):
        assert ResponseTransformer.transform({"places": []}) == []

    def test_places_none_returns_empty(self):
        assert ResponseTransformer.transform({"places": None}) == []


# ---------------------------------------------------------------------------
# Tests: single place, minimal data
# ---------------------------------------------------------------------------


class TestTransformSinglePlace:
    def test_minimal_place_produces_one_recommendation(self):
        data = _pipeline([_make_place()])
        result = ResponseTransformer.transform(data)

        assert len(result) == 1
        rec = result[0]
        assert rec["id"] == "pid_1"
        assert rec["name"] == "Museo del Prado"
        assert rec["type"] == "museum"

    def test_venue_built_from_place(self):
        data = _pipeline([_make_place(rating=4.0)])
        rec = ResponseTransformer.transform(data)[0]

        assert rec["venue"] is not None
        assert rec["venue"]["name"] == "Museo del Prado"
        assert rec["venue"]["type"] == "museum"
        assert rec["venue"]["accessibility_score"] == 4.0

    def test_confidence_normalized_from_rating(self):
        data = _pipeline([_make_place(rating=5.0)])
        rec = ResponseTransformer.transform(data)[0]
        assert rec["confidence"] == 1.0

        data2 = _pipeline([_make_place(rating=2.5)])
        rec2 = ResponseTransformer.transform(data2)[0]
        assert rec2["confidence"] == 0.5

    def test_maps_url_from_place_id(self):
        data = _pipeline([_make_place(place_id="abc")])
        rec = ResponseTransformer.transform(data)[0]
        assert "place_id:abc" in rec["maps_url"]

    def test_maps_url_from_coords_when_no_place_id(self):
        place = _make_place(place_id=None)
        data = _pipeline([place])
        rec = ResponseTransformer.transform(data)[0]
        assert "40.4138" in rec["maps_url"]
        assert "-3.6921" in rec["maps_url"]

    def test_no_accessibility_when_map_empty(self):
        data = _pipeline([_make_place()])
        rec = ResponseTransformer.transform(data)[0]
        assert rec["accessibility"] is None

    def test_no_routes_when_map_empty(self):
        data = _pipeline([_make_place()])
        rec = ResponseTransformer.transform(data)[0]
        assert rec["routes"] == []


# ---------------------------------------------------------------------------
# Tests: accessibility enrichment
# ---------------------------------------------------------------------------


class TestTransformAccessibility:
    def test_accessibility_mapped_from_acc_map(self):
        acc = _make_acc(level="good", score=8.0, entrance=True, parking=True)
        data = _pipeline(
            [_make_place(place_id="p1")],
            acc_map={"p1": acc},
        )
        rec = ResponseTransformer.transform(data)[0]

        assert rec["accessibility"] is not None
        assert rec["accessibility"]["level"] == "good"
        assert rec["accessibility"]["score"] == 8.0
        assert "Entrada accesible" in rec["accessibility"]["services"]
        assert rec["accessibility"]["services"]["Entrada accesible"] == "Sí"
        assert rec["accessibility"]["services"]["Parking accesible"] == "Sí"

    def test_wheelchair_false_mapped_as_no(self):
        acc = _make_acc(entrance=False, parking=False)
        data = _pipeline([_make_place(place_id="p1")], acc_map={"p1": acc})
        rec = ResponseTransformer.transform(data)[0]

        assert rec["accessibility"]["services"]["Entrada accesible"] == "No"

    def test_wheelchair_none_omitted_from_services(self):
        acc = _make_acc()
        # restroom and seating are None by default
        data = _pipeline([_make_place(place_id="p1")], acc_map={"p1": acc})
        rec = ResponseTransformer.transform(data)[0]

        services = rec["accessibility"].get("services", {})
        assert "Aseo accesible" not in services
        assert "Asiento accesible" not in services

    def test_acc_score_merged_into_venue(self):
        place = _make_place(place_id="p1", rating=None)
        acc = _make_acc(score=9.0)
        data = _pipeline([place], acc_map={"p1": acc})
        rec = ResponseTransformer.transform(data)[0]

        assert rec["venue"]["accessibility_score"] == 9.0


# ---------------------------------------------------------------------------
# Tests: routes enrichment
# ---------------------------------------------------------------------------


class TestTransformRoutes:
    def test_routes_mapped_from_routes_map(self):
        route = _make_route(transport="bus", duration_minutes=20, acc_score=0.5)
        data = _pipeline(
            [_make_place(place_id="p1")],
            routes_map={"p1": [route]},
        )
        rec = ResponseTransformer.transform(data)[0]

        assert len(rec["routes"]) == 1
        r = rec["routes"][0]
        assert r["transport"] == "bus"
        assert r["duration"] == "20 min"
        assert r["accessibility"] == "partial"
        assert r["cost"] == "1.50€"
        assert r["steps"] is not None
        assert len(r["steps"]) == 2

    def test_route_full_accessibility_threshold(self):
        route = _make_route(acc_score=0.8)
        data = _pipeline([_make_place(place_id="p1")], routes_map={"p1": [route]})
        rec = ResponseTransformer.transform(data)[0]
        assert rec["routes"][0]["accessibility"] == "full"

    def test_route_steps_from_dict_format(self):
        route = _make_route()
        route["steps"] = [{"instruction": "Gira a la derecha"}, {"description": "Sigue recto"}]
        data = _pipeline([_make_place(place_id="p1")], routes_map={"p1": [route]})
        rec = ResponseTransformer.transform(data)[0]

        assert rec["routes"][0]["steps"][0] == "Gira a la derecha"
        assert rec["routes"][0]["steps"][1] == "Sigue recto"


# ---------------------------------------------------------------------------
# Tests: multi-place sorting
# ---------------------------------------------------------------------------


class TestTransformMultiPlace:
    def test_sorted_by_accessibility_score_desc(self):
        places = [
            _make_place(name="Low", place_id="low", rating=2.0),
            _make_place(name="High", place_id="high", rating=4.0),
        ]
        acc_map = {
            "low": _make_acc(score=3.0),
            "high": _make_acc(score=9.0),
        }
        data = _pipeline(places, acc_map=acc_map)
        result = ResponseTransformer.transform(data)

        assert len(result) == 2
        assert result[0]["name"] == "High"
        assert result[1]["name"] == "Low"

    def test_three_places_all_returned(self):
        places = [_make_place(name=f"P{i}", place_id=f"p{i}") for i in range(3)]
        data = _pipeline(places)
        result = ResponseTransformer.transform(data)
        assert len(result) == 3

    def test_bad_place_skipped_gracefully(self):
        places = [
            _make_place(name="Good", place_id="good"),
            {"weird_field": True},  # malformed
        ]
        data = _pipeline(places)
        result = ResponseTransformer.transform(data)
        # At minimum the good one should be present
        assert any(r["name"] == "Good" for r in result)


# ---------------------------------------------------------------------------
# Tests: Pydantic validation
# ---------------------------------------------------------------------------


class TestPydanticValidation:
    def test_confidence_clamped_to_0_1(self):
        place = _make_place(rating=6.0)  # 6/5 = 1.2 -> clamped to 1.0
        data = _pipeline([place])
        rec = ResponseTransformer.transform(data)[0]
        assert rec["confidence"] == 1.0

    def test_output_is_serializable_dict(self):
        acc = _make_acc(score=7.0)
        route = _make_route()
        data = _pipeline(
            [_make_place(place_id="p1")],
            acc_map={"p1": acc},
            routes_map={"p1": [route]},
        )
        result = ResponseTransformer.transform(data)

        # Should be plain dicts, not Pydantic models
        assert isinstance(result[0], dict)
        assert isinstance(result[0]["venue"], dict)
        assert isinstance(result[0]["routes"][0], dict)

    def test_place_without_name_gets_default(self):
        place = {"place_id": "x", "rating": 3.0}
        data = _pipeline([place])
        result = ResponseTransformer.transform(data)
        assert len(result) == 1
        assert result[0]["name"] == "Recomendación"
