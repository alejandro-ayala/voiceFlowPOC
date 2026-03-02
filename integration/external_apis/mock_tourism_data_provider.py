"""Mock provider for high-level tourism capabilities.

This provider is intentionally local and deterministic for integration wiring.
It does not rely on project JSON fixture files.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from shared.interfaces.tourism_data_provider_interface import TourismDataProviderInterface


class MockTourismDataProvider(TourismDataProviderInterface):
    """Deterministic provider used as first step before real external APIs."""

    _venue_index = {
        "barcelona": {
            "name": "Museu Nacional d'Art de Catalunya",
            "type": "museum",
            "opening_hours": {"today": "10:00-20:00"},
            "pricing": {"general": "12€", "reduced": "6€", "free": "Domingos tarde"},
            "facilities": ["wheelchair_ramps", "adapted_bathrooms", "audio_guides", "elevator_access"],
        },
        "madrid": {
            "name": "Museo del Prado",
            "type": "museum",
            "opening_hours": {"today": "10:00-20:00"},
            "pricing": {"general": "15€", "reduced": "7.5€", "free": "Personas con discapacidad + acompañante"},
            "facilities": [
                "wheelchair_ramps",
                "adapted_bathrooms",
                "audio_guides",
                "tactile_paths",
                "elevator_access",
                "sign_language_interpreters",
            ],
        },
        "valencia": {
            "name": "Ciudad de las Artes y las Ciencias",
            "type": "entertainment",
            "opening_hours": {"today": "10:00-19:00"},
            "pricing": {"general": "38€", "reduced": "31€"},
            "facilities": ["wheelchair_ramps", "adapted_bathrooms", "elevator_access"],
        },
    }

    def is_service_available(self) -> bool:
        return True

    @staticmethod
    def _build_accessibility_match(accessibility_need: Optional[str], facilities: list[str]) -> dict[str, Any]:
        required_by_need = {
            "wheelchair": ["wheelchair_ramps", "adapted_bathrooms", "elevator_access"],
            "visual_impairment": ["audio_guides", "tactile_paths"],
            "hearing_impairment": ["hearing_loops", "sign_language_interpreters"],
            "cognitive": ["easy_read_signage"],
        }

        if not isinstance(accessibility_need, str) or accessibility_need not in required_by_need:
            return {
                "score": 0.5,
                "matched_requirements": [],
                "missing_requirements": [],
                "requirements_source": "unknown",
                "notes": "TODO: profile explicit accessibility requirements are not defined",
            }

        requirements = required_by_need[accessibility_need]
        normalized_facilities = [item.lower().strip() for item in facilities if isinstance(item, str)]
        matched = [item for item in requirements if item in normalized_facilities]
        missing = [item for item in requirements if item not in normalized_facilities]

        return {
            "score": round(len(matched) / len(requirements), 3),
            "matched_requirements": matched,
            "missing_requirements": missing,
            "requirements_source": "query_inferred",
            "notes": None,
        }

    @staticmethod
    def _score_venue_type(profile_context: Optional[dict[str, Any]], venue_type: str) -> float:
        if not isinstance(profile_context, dict):
            return 1.0

        ranking_bias = profile_context.get("ranking_bias")
        if not isinstance(ranking_bias, dict):
            return 1.0

        venue_types = ranking_bias.get("venue_types")
        if not isinstance(venue_types, dict):
            return 1.0

        value = venue_types.get(venue_type)
        if isinstance(value, (int, float)):
            return float(value)
        return 1.0

    def get_service_info(self) -> dict[str, Any]:
        return {
            "provider": "mock_tourism_data_provider",
            "available": True,
            "mode": "deterministic",
            "supports_external_calls": False,
        }

    def _resolve_destination_key(self, destination: Optional[str], query_text: Optional[str] = None) -> str:
        value = f"{destination or ''} {query_text or ''}".lower()
        for city in self._venue_index.keys():
            if city in value:
                return city
        return "madrid"

    def get_accessibility_insights(
        self,
        destination: Optional[str],
        accessibility_need: Optional[str],
        profile_context: Optional[dict[str, Any]] = None,
        language: str = "es",
    ) -> dict[str, Any]:
        city_key = self._resolve_destination_key(destination)
        venue = self._venue_index[city_key]

        del profile_context
        accessibility_match = self._build_accessibility_match(
            accessibility_need=accessibility_need,
            facilities=venue.get("facilities", []),
        )

        return {
            "status": "ok",
            "destination": destination or city_key.title(),
            "language": language,
            "accessibility_level": "high" if accessibility_match["score"] >= 0.66 else "medium",
            "accessibility_score": round(6.5 + 3.0 * accessibility_match["score"], 2),
            "facilities": venue.get("facilities", []),
            "certification": "mock_verified",
            "profile_accessibility_match": accessibility_match,
            "last_updated": datetime.now().isoformat(),
        }

    def plan_routes(
        self,
        origin_text: Optional[str],
        destination: Optional[str],
        accessibility_need: Optional[str],
        profile_context: Optional[dict[str, Any]] = None,
        language: str = "es",
    ) -> dict[str, Any]:
        del profile_context
        city_key = self._resolve_destination_key(destination, query_text=origin_text)

        avoid = []
        if accessibility_need == "wheelchair":
            avoid.append("stations_without_elevator")

        route = {
            "transport": "metro",
            "line": "L1",
            "duration": "22 min",
            "accessibility": "full" if accessibility_need == "wheelchair" else "partial",
            "cost": "1.5€",
            "steps": [
                f"Salida desde ubicación aproximada en {city_key.title()}",
                "Usar accesos señalizados como accesibles",
                "Llegada al destino por entrada principal accesible",
            ],
        }

        return {
            "status": "ok",
            "destination": destination or city_key.title(),
            "language": language,
            "routes": [route],
            "alternatives": ["accessible_taxi", "walking"],
            "estimated_cost": route["cost"],
            "constraints_applied": avoid,
        }

    def get_tourism_info(
        self,
        destination: Optional[str],
        query_text: Optional[str],
        profile_context: Optional[dict[str, Any]] = None,
        language: str = "es",
    ) -> dict[str, Any]:
        city_key = self._resolve_destination_key(destination, query_text=query_text)
        venue = self._venue_index[city_key]

        venue_type = venue.get("type", "tourism")
        profile_weight = self._score_venue_type(profile_context, venue_type)

        accessibility_match = self._build_accessibility_match(
            accessibility_need=None,
            facilities=venue.get("facilities", []),
        )

        return {
            "status": "ok",
            "language": language,
            "venue": {
                "name": venue.get("name"),
                "type": venue_type,
                "accessibility_score": round(7.0 * profile_weight, 2),
                "facilities": venue.get("facilities", []),
                "opening_hours": venue.get("opening_hours", {}),
                "pricing": venue.get("pricing", {}),
            },
            "opening_hours": venue.get("opening_hours", {}),
            "pricing": venue.get("pricing", {}),
            "current_crowds": "moderate",
            "free_access_for_disability": True,
            "profile_accessibility_match": accessibility_match,
            "profile_ranking_weight": profile_weight,
            "provider": "mock_tourism_data_provider",
            "last_updated": datetime.now().isoformat(),
        }
