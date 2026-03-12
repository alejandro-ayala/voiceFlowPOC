"""Transforms pipeline tool outputs into UI-consumable Recommendation list.

This module is the boundary between the internal ToolPipelineContext contract
(business layer) and the stable API response contract (application layer).
The UI should consume recommendations[], never raw tool outputs.
"""

from typing import Any, Optional
from uuid import uuid4

import structlog

from application.models.responses import Recommendation

logger = structlog.get_logger(__name__)


class ResponseTransformer:
    """Pure transformation: pipeline_context data -> Recommendation list."""

    @staticmethod
    def transform(
        pipeline_data: dict[str, Any],
        profile_context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Transform pipeline_context from metadata into validated Recommendation dicts.

        Args:
            pipeline_data: metadata["pipeline_context"] from AgentResponse.
                Expected keys: places (list), accessibility_map (dict), routes_map (dict).
            profile_context: optional profile for future ranking bias.

        Returns:
            List of Recommendation-compatible dicts, ordered by accessibility score desc.
        """
        if not pipeline_data:
            return []

        places = pipeline_data.get("places") or []
        if not places:
            return []

        acc_map = pipeline_data.get("accessibility_map") or {}
        routes_map = pipeline_data.get("routes_map") or {}

        recommendations: list[dict[str, Any]] = []
        for place in places:
            try:
                rec = ResponseTransformer._build_recommendation(place, acc_map, routes_map)
                recommendations.append(rec)
            except Exception as exc:
                logger.warning(
                    "recommendation_build_failed",
                    place_name=place.get("name"),
                    error=str(exc),
                )

        # Sort: accessibility score desc, then confidence desc
        recommendations.sort(
            key=lambda r: (
                ResponseTransformer._sort_score(r),
                r.get("confidence") or 0,
            ),
            reverse=True,
        )

        # Validate each recommendation through Pydantic
        validated: list[dict[str, Any]] = []
        for rec_data in recommendations:
            try:
                rec_model = Recommendation.model_validate(rec_data)
                validated.append(rec_model.model_dump())
            except Exception as exc:
                logger.warning(
                    "recommendation_validation_failed",
                    rec_id=rec_data.get("id"),
                    error=str(exc),
                )

        return validated

    @staticmethod
    def _build_recommendation(
        place: dict[str, Any],
        acc_map: dict[str, Any],
        routes_map: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a single Recommendation dict from place + enrichment data."""
        place_id = place.get("place_id") or str(uuid4())
        place_types = place.get("types") or []
        place_type = place_types[0] if place_types else (place.get("place_type") or "venue")

        # Build venue from place data
        venue = ResponseTransformer._build_venue(place)

        # Lookup accessibility from map
        accessibility = ResponseTransformer._build_accessibility(acc_map.get(place_id))

        # Lookup routes from map
        routes = ResponseTransformer._build_routes(routes_map.get(place_id))

        # Merge accessibility score into venue if available
        if accessibility and venue:
            acc_score = accessibility.get("score")
            if acc_score is not None and venue.get("accessibility_score") is None:
                venue["accessibility_score"] = acc_score

        return {
            "id": place_id,
            "name": place.get("name") or "Recomendación",
            "type": place_type,
            "summary": None,
            "venue": venue,
            "accessibility": accessibility,
            "routes": routes,
            "maps_url": ResponseTransformer._build_maps_url(place),
            "source": place.get("source"),
            "confidence": ResponseTransformer._normalize_confidence(place),
        }

    @staticmethod
    def _build_venue(place: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Build a Venue dict from place candidate data."""
        name = place.get("name")
        if not name:
            return None

        place_types = place.get("types") or []
        place_type = place_types[0] if place_types else (place.get("place_type") or "venue")

        return {
            "name": name,
            "type": place_type,
            "accessibility_score": place.get("rating"),
            "facilities": [],
        }

    @staticmethod
    def _build_accessibility(acc_data: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Build an Accessibility dict from accessibility_map entry."""
        if not acc_data:
            return None

        # Map from AccessibilityInfo field names to Accessibility model field names
        level = acc_data.get("accessibility_level")
        score = acc_data.get("accessibility_score")
        facilities = acc_data.get("facilities") or []
        certification = acc_data.get("certification")
        warnings = acc_data.get("warnings") or []

        # Build services dict from wheelchair fields
        services: dict[str, str] = {}
        wc_fields = {
            "wheelchair_accessible_entrance": "Entrada accesible",
            "wheelchair_accessible_parking": "Parking accesible",
            "wheelchair_accessible_restroom": "Aseo accesible",
            "wheelchair_accessible_seating": "Asiento accesible",
        }
        for field_key, label in wc_fields.items():
            value = acc_data.get(field_key)
            if isinstance(value, bool):
                services[label] = "Sí" if value else "No"

        result: dict[str, Any] = {
            "level": level,
            "score": score,
            "certification": certification,
            "facilities": facilities,
        }
        if services:
            result["services"] = services
        if warnings:
            result["warnings"] = warnings

        return result

    @staticmethod
    def _build_routes(routes_data: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """Build Route dicts from routes_map entry."""
        if not routes_data:
            return []

        routes: list[dict[str, Any]] = []
        for r in routes_data:
            # Map from RouteOption field names to Route model field names
            duration_min = r.get("duration_minutes")
            duration_str = f"{duration_min} min" if duration_min is not None else r.get("description")

            steps_raw = r.get("steps") or []
            steps: list[str] = []
            for s in steps_raw:
                if isinstance(s, str):
                    steps.append(s)
                elif isinstance(s, dict):
                    steps.append(s.get("instruction") or s.get("description") or str(s))

            routes.append(
                {
                    "transport": r.get("transport_type"),
                    "line": None,
                    "duration": duration_str,
                    "accessibility": "full" if (r.get("accessibility_score") or 0) >= 0.8 else "partial",
                    "cost": r.get("estimated_cost"),
                    "steps": steps or None,
                }
            )

        return routes

    @staticmethod
    def _build_maps_url(place: dict[str, Any]) -> Optional[str]:
        """Build a Google Maps deep link from place data."""
        place_id = place.get("place_id")
        if place_id:
            return f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        lat = place.get("location_lat")
        lng = place.get("location_lng")
        if lat is not None and lng is not None:
            return f"https://www.google.com/maps/@{lat},{lng},17z"

        return None

    @staticmethod
    def _normalize_confidence(place: dict[str, Any]) -> Optional[float]:
        """Normalize rating (0-5) to confidence (0-1)."""
        rating = place.get("rating")
        if rating is not None:
            try:
                return min(float(rating) / 5.0, 1.0)
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _sort_score(rec: dict[str, Any]) -> float:
        """Extract sort score from a recommendation dict."""
        acc = rec.get("accessibility")
        if isinstance(acc, dict):
            score = acc.get("score")
            if isinstance(score, (int, float)):
                return float(score)
        return 0.0
