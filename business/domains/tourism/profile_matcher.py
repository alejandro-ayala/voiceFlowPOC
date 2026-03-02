"""Profile-driven ranking and accessibility comparison helpers."""

from __future__ import annotations

from typing import Any, Optional


class ProfileMatcher:
    """Pure helper methods for profile-based ranking and comparison."""

    @staticmethod
    def score_venue_type(profile_context: Optional[dict[str, Any]], venue_type: str) -> float:
        if not isinstance(profile_context, dict):
            return 1.0

        ranking_bias = profile_context.get("ranking_bias")
        if not isinstance(ranking_bias, dict):
            return 1.0

        venue_types = ranking_bias.get("venue_types")
        if not isinstance(venue_types, dict):
            return 1.0

        raw_score = venue_types.get(venue_type)
        if isinstance(raw_score, (int, float)):
            return float(raw_score)
        return 1.0

    @staticmethod
    def build_accessibility_match(
        profile_context: Optional[dict[str, Any]],
        facilities: list[str],
        accessibility_need: Optional[str],
    ) -> dict[str, Any]:
        normalized_facilities = [f.lower().strip() for f in facilities if isinstance(f, str)]

        required_by_need = {
            "wheelchair": ["wheelchair_ramps", "adapted_bathrooms", "elevator_access"],
            "visual_impairment": ["audio_guides", "tactile_paths"],
            "hearing_impairment": ["hearing_loops", "sign_language_interpreters"],
            "cognitive": ["easy_read_signage"],
        }

        inferred_requirements: list[str] = []
        source = "unknown"
        if isinstance(accessibility_need, str) and accessibility_need in required_by_need:
            inferred_requirements = required_by_need[accessibility_need]
            source = "query_inferred"

        if not inferred_requirements:
            return {
                "score": 0.5,
                "matched_requirements": [],
                "missing_requirements": [],
                "requirements_source": source,
                "notes": "TODO: profile_context currently has no explicit accessibility requirements",
            }

        matched = [req for req in inferred_requirements if req in normalized_facilities]
        missing = [req for req in inferred_requirements if req not in normalized_facilities]
        score = len(matched) / len(inferred_requirements)

        return {
            "score": round(score, 3),
            "matched_requirements": matched,
            "missing_requirements": missing,
            "requirements_source": source,
            "notes": None,
        }
