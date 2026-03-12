"""Places search tool using pluggable PlacesServiceInterface."""

import json
import re
import unicodedata
from dataclasses import dataclass

import structlog

from shared.interfaces.places_interface import PlacesServiceInterface
from shared.models.nlu_models import NLUEntitySet
from shared.models.tool_models import ToolError, ToolPipelineContext

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class IntentSearchPolicy:
    """Intent-specific search behavior for places discovery."""

    type_filter: str | None = None
    query_hint: str | None = None
    preferred_types: tuple[str, ...] = ()


class PlacesSearchTool:
    """Search for places and retrieve venue details via an injected PlacesServiceInterface."""

    _INTENT_POLICIES: dict[str, IntentSearchPolicy] = {
        "restaurant_search": IntentSearchPolicy(
            type_filter="restaurant",
            query_hint="restaurante accesible",
            preferred_types=("restaurant", "food", "meal_takeaway", "cafe"),
        ),
        "accommodation_search": IntentSearchPolicy(
            type_filter="lodging",
            query_hint="hotel accesible",
            preferred_types=("lodging", "hotel"),
        ),
        "event_search": IntentSearchPolicy(
            query_hint="ocio accesible",
            preferred_types=("tourist_attraction", "event_venue", "night_club", "bar", "theater"),
        ),
        "museum_search": IntentSearchPolicy(
            type_filter="museum",
            query_hint="museo",
            preferred_types=("museum", "tourist_attraction"),
        ),
        "cultural_visit": IntentSearchPolicy(
            query_hint="museo cultural",
            preferred_types=("museum", "art_gallery", "tourist_attraction"),
        ),
        "route_planning": IntentSearchPolicy(
            query_hint=None,
            preferred_types=("tourist_attraction", "museum", "restaurant", "lodging", "point_of_interest"),
        ),
    }

    _GENERIC_DESTINATIONS = {
        "general",
        "general_query",
        "none",
        "null",
        "unknown",
        "madrid centro",
    }

    def __init__(self, places_service: PlacesServiceInterface):
        self._service = places_service

    async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
        """Search by place name from ctx, populate ctx.place and ctx.venue_detail."""
        intent = self._resolve_intent(ctx)
        policy = self._policy_for_intent(intent)

        query_original = self._build_query(ctx)
        destination = self._extract_destination(ctx)
        query_final = self._apply_query_hint(query_original, policy)
        query_final = self._dedupe_text(query_final)
        location_final, dedupe_applied = self._normalize_location_for_query(
            query=query_final,
            location=destination,
        )

        if not query_final:
            logger.info(
                "places_search_skipped_empty_query",
                intent=intent,
                query_original=query_original,
            )
            return ctx

        try:
            candidates = await self._service.text_search(
                query=query_final,
                location=location_final,
                type_filter=policy.type_filter,
                language=ctx.language,
                max_results=5,
            )

            ranked_candidates = self._rank_candidates(
                candidates=candidates,
                intent=intent,
                destination=destination,
                preferred_types=policy.preferred_types,
            )
            selected_candidates = ranked_candidates[:3]

            if selected_candidates:
                ctx.place = selected_candidates[0]
                ctx.places = list(selected_candidates)

                if selected_candidates[0].place_id:
                    detail = await self._service.place_details(
                        place_id=selected_candidates[0].place_id,
                        language=ctx.language,
                    )
                    ctx.venue_detail = detail

                    google_accessibility = self._extract_google_accessibility(
                        venue_detail=detail,
                        candidate=selected_candidates[0],
                    )
                    if google_accessibility:
                        ctx.raw_tool_results["accessibility_google"] = json.dumps(
                            google_accessibility,
                            ensure_ascii=False,
                        )

                ctx.raw_tool_results["venue info"] = json.dumps(
                    [c.model_dump() for c in selected_candidates],
                    ensure_ascii=False,
                )

            logger.info(
                "places_search_complete",
                intent=intent,
                query_original=query_original,
                query_final=query_final,
                location_final=location_final,
                dedupe_applied=dedupe_applied,
                type_filter=policy.type_filter,
                results_total=len(candidates),
                results_selected=len(selected_candidates),
                source=self._service.get_service_info().get("provider"),
            )

        except Exception as exc:
            logger.warning(
                "places_search_failed",
                intent=intent,
                query_original=query_original,
                query_final=query_final,
                location_final=location_final,
                type_filter=policy.type_filter,
                error=str(exc),
            )
            ctx.errors.append(ToolError(source="places_search", message=str(exc)))

        return ctx

    @staticmethod
    def _build_query(ctx: ToolPipelineContext) -> str:
        if ctx.place and ctx.place.name:
            return ctx.place.name
        if ctx.nlu_result and ctx.nlu_result.entities:
            entities = ctx.nlu_result.entities
            dest = entities.destination if isinstance(entities, NLUEntitySet) else None
            if dest:
                return dest
        return ctx.user_input

    @classmethod
    def _resolve_intent(cls, ctx: ToolPipelineContext) -> str:
        if ctx.nlu_result and isinstance(ctx.nlu_result.intent, str) and ctx.nlu_result.intent.strip():
            return ctx.nlu_result.intent.strip().lower()
        return "general_query"

    @classmethod
    def _policy_for_intent(cls, intent: str) -> IntentSearchPolicy:
        return cls._INTENT_POLICIES.get(intent, IntentSearchPolicy())

    @classmethod
    def _extract_destination(cls, ctx: ToolPipelineContext) -> str | None:
        if ctx.place and isinstance(ctx.place.destination, str) and ctx.place.destination.strip():
            return ctx.place.destination.strip()

        if ctx.nlu_result and isinstance(ctx.nlu_result.entities, NLUEntitySet):
            value = ctx.nlu_result.entities.destination
            if isinstance(value, str) and value.strip() and cls._normalize(value) not in cls._GENERIC_DESTINATIONS:
                return value.strip()

        return None

    @classmethod
    def _apply_query_hint(cls, query: str, policy: IntentSearchPolicy) -> str:
        base = (query or "").strip()
        if not base:
            return ""

        hint = (policy.query_hint or "").strip()
        if not hint:
            return base

        base_norm = cls._normalize(base)
        hint_norm = cls._normalize(hint)
        if hint_norm and hint_norm in base_norm:
            return base

        return f"{base} {hint}".strip()

    @classmethod
    def _normalize_location_for_query(cls, query: str, location: str | None) -> tuple[str | None, bool]:
        if not location:
            return None, False

        query_norm = cls._normalize(query)
        location_norm = cls._normalize(location)

        if not location_norm:
            return None, False

        if query_norm == location_norm or location_norm in query_norm:
            return None, True

        return location.strip(), False

    @classmethod
    def _dedupe_text(cls, value: str) -> str:
        tokens = [token for token in re.split(r"\s+", (value or "").strip()) if token]
        if not tokens:
            return ""

        deduped: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            normalized = cls._normalize(token)
            if normalized and normalized in seen:
                continue
            if normalized:
                seen.add(normalized)
            deduped.append(token)

        return " ".join(deduped)

    @classmethod
    def _rank_candidates(
        cls,
        candidates,
        intent: str,
        destination: str | None,
        preferred_types: tuple[str, ...],
    ):
        destination_norm = cls._normalize(destination or "")
        preferred = {cls._normalize(item) for item in preferred_types}

        def score(candidate) -> tuple[int, float]:
            score_value = 0

            candidate_types = []
            if isinstance(getattr(candidate, "types", None), list):
                candidate_types = [cls._normalize(item) for item in candidate.types if isinstance(item, str)]

            place_type = cls._normalize(getattr(candidate, "place_type", None) or "")
            candidate_type_set = set(candidate_types + ([place_type] if place_type else []))

            if preferred and candidate_type_set.intersection(preferred):
                score_value += 3

            name_norm = cls._normalize(getattr(candidate, "name", "") or "")
            if destination_norm and destination_norm in name_norm:
                score_value += 2

            rating = getattr(candidate, "rating", None)
            rating_value = float(rating) if isinstance(rating, (int, float)) else 0.0
            return (score_value, rating_value)

        return sorted(candidates, key=score, reverse=True)

    @staticmethod
    def _normalize(value: str | None) -> str:
        if not isinstance(value, str):
            return ""
        normalized = unicodedata.normalize("NFKD", value)
        ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", ascii_text).strip().lower()

    @classmethod
    def _extract_google_accessibility(cls, venue_detail, candidate) -> dict | None:
        reviews = getattr(venue_detail, "accessibility_reviews", None)
        if not isinstance(reviews, dict):
            return None

        options = reviews.get("accessibility_options")
        if not isinstance(options, dict) or not options:
            return None

        normalized = {
            "wheelchair_accessible_entrance": options.get("wheelchairAccessibleEntrance"),
            "wheelchair_accessible_parking": options.get("wheelchairAccessibleParking"),
            "wheelchair_accessible_restroom": options.get("wheelchairAccessibleRestroom"),
            "wheelchair_accessible_seating": options.get("wheelchairAccessibleSeating"),
        }

        known_flags = [value for value in normalized.values() if isinstance(value, bool)]
        positives = sum(1 for value in known_flags if value)
        accessibility_score = round(positives / len(known_flags), 2) if known_flags else 0.0
        accessibility_level = "unknown"
        if known_flags:
            if positives == len(known_flags):
                accessibility_level = "full"
            elif positives > 0:
                accessibility_level = "partial"
            else:
                accessibility_level = "limited"

        return {
            "source": "google_places",
            "place_id": getattr(candidate, "place_id", None),
            "place_name": getattr(venue_detail, "name", None),
            "accessibility_options_raw": options,
            "normalized": normalized,
            "accessibility_level": accessibility_level,
            "accessibility_score": accessibility_score,
        }
