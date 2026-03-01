"""Entity resolver for deterministic merge of NLU and NER outputs."""

from __future__ import annotations

import structlog

from shared.models.nlu_models import NLUResult, ResolvedEntities

logger = structlog.get_logger(__name__)


class EntityResolver:
    """Merge NLU entities with NER location extraction using deterministic rules."""

    GENERIC_DESTINATIONS = {"general", "general_query", "madrid centro", "none", "null", ""}

    def resolve(
        self,
        nlu_result: NLUResult,
        ner_locations: list[str],
        ner_top_location: str | None,
    ) -> ResolvedEntities:
        nlu_destination = nlu_result.entities.destination
        conflicts: list[str] = []
        resolution_source: dict[str, str] = {}

        nlu_normalized = self._normalize_name(nlu_destination)
        ner_normalized = self._normalize_name(ner_top_location)

        if not nlu_normalized and not ner_normalized:
            resolved_destination = None
            resolution_source["destination"] = "none"
        elif not nlu_normalized and ner_top_location:
            resolved_destination = ner_top_location
            resolution_source["destination"] = "ner"
        elif nlu_destination and not ner_normalized:
            resolved_destination = nlu_destination
            resolution_source["destination"] = "nlu"
        elif nlu_destination and ner_top_location and nlu_normalized == ner_normalized:
            resolved_destination = nlu_destination
            resolution_source["destination"] = "both_agree"
        elif nlu_destination and ner_top_location and self._contains_either(nlu_destination, ner_top_location):
            resolved_destination = nlu_destination
            resolution_source["destination"] = "nlu_normalized"
        elif self._is_generic(nlu_destination) and ner_top_location:
            resolved_destination = ner_top_location
            resolution_source["destination"] = "ner_override"
            conflicts.append(f"NLU='{nlu_destination}' generic, NER='{ner_top_location}' specific → NER used")
        else:
            resolved_destination = nlu_destination
            resolution_source["destination"] = "nlu_preferred"
            conflicts.append(f"Conflict: NLU='{nlu_destination}' vs NER='{ner_top_location}' → NLU preferred")

        for field in ("accessibility", "timeframe", "transport_preference", "budget"):
            value = getattr(nlu_result.entities, field, None)
            resolution_source[field] = "nlu" if value else "none"

        if conflicts:
            logger.warning("entity_resolver_conflicts", conflicts=conflicts)

        return ResolvedEntities(
            destination=resolved_destination,
            locations=ner_locations,
            top_location=ner_top_location,
            accessibility=nlu_result.entities.accessibility,
            timeframe=nlu_result.entities.timeframe,
            transport_preference=nlu_result.entities.transport_preference,
            budget=nlu_result.entities.budget,
            resolution_source=resolution_source,
            conflicts=conflicts,
        )

    @staticmethod
    def _normalize_name(name: str | None) -> str | None:
        if not isinstance(name, str):
            return None
        cleaned = name.strip().lower()
        return cleaned or None

    @classmethod
    def _is_generic(cls, name: str | None) -> bool:
        normalized = cls._normalize_name(name)
        return normalized in cls.GENERIC_DESTINATIONS

    @staticmethod
    def _contains_either(left: str, right: str) -> bool:
        left_n = left.lower().strip()
        right_n = right.lower().strip()
        return left_n in right_n or right_n in left_n
