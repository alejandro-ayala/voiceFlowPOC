"""Accessibility enrichment tool using pluggable AccessibilityServiceInterface."""

import json
from typing import Any

import structlog

from integration.configuration.settings import Settings
from shared.interfaces.accessibility_interface import AccessibilityServiceInterface
from shared.models.tool_models import ToolError, ToolPipelineContext

logger = structlog.get_logger(__name__)


class AccessibilityEnrichmentTool:
    """Enrich place data with accessibility info via an injected service."""

    def __init__(self, accessibility_service: AccessibilityServiceInterface):
        self._service = accessibility_service
        self._debug_raw_enabled = Settings().accessibility_debug_raw

    async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
        """Enrich ctx.place with accessibility data, populate ctx.accessibility."""
        place_name = self._resolve_place_name(ctx)
        if not place_name:
            return ctx

        try:
            google_accessibility = self._load_google_accessibility(ctx)
            logger.info(
                "accessibility_enrichment_started",
                place=place_name,
                place_id=ctx.place.place_id if ctx.place else None,
                location=ctx.place.destination if ctx.place else None,
                provider=self._service.get_service_info().get("provider"),
                has_google_accessibility=bool(google_accessibility),
            )

            info = await self._service.enrich_accessibility(
                place_name=place_name,
                place_id=ctx.place.place_id if ctx.place else None,
                location=ctx.place.destination if ctx.place else None,
                latitude=ctx.place.location_lat if ctx.place else None,
                longitude=ctx.place.location_lng if ctx.place else None,
                language=ctx.language,
            )

            provider_debug = self._service.get_debug_snapshot() or {}
            overpass_normalized = self._extract_overpass_normalized(provider_debug)
            merged_info = self._merge_with_google(info, google_accessibility)
            comparison = self._build_comparison(
                google_accessibility=google_accessibility,
                merged=merged_info.model_dump(),
                provider=provider_debug,
                include_provider_raw=self._debug_raw_enabled,
            )

            ctx.accessibility = merged_info
            ctx.raw_tool_results["accessibility"] = json.dumps(
                merged_info.model_dump(),
                ensure_ascii=False,
            )
            if overpass_normalized:
                ctx.raw_tool_results["accessibility_overpass_normalized"] = json.dumps(
                    overpass_normalized,
                    ensure_ascii=False,
                )
            if self._debug_raw_enabled:
                ctx.raw_tool_results["accessibility_overpass_raw"] = json.dumps(
                    provider_debug,
                    ensure_ascii=False,
                )
            ctx.raw_tool_results["accessibility_comparison"] = json.dumps(
                comparison,
                ensure_ascii=False,
            )

            logger.info(
                "accessibility_enrichment_complete",
                place=place_name,
                level=merged_info.accessibility_level,
                source=self._service.get_service_info().get("provider"),
                has_google_accessibility=bool(google_accessibility),
                debug_raw_enabled=self._debug_raw_enabled,
                overpass_payload_keys=(
                    list((provider_debug.get("response_raw") or {}).keys())
                    if isinstance(provider_debug, dict)
                    else []
                ),
                comparison_conflicts=len(comparison.get("conflicts") or []),
            )

        except Exception as exc:
            provider_name = self._service.get_service_info().get("provider")
            logger.warning(
                "accessibility_enrichment_failed "
                f"place={place_name} provider={provider_name} "
                f"error_type={type(exc).__name__} error={repr(exc)}"
            )
            ctx.errors.append(ToolError(source="accessibility_enrichment", message=str(exc)))

        return ctx

    @staticmethod
    def _resolve_place_name(ctx: ToolPipelineContext) -> str:
        if ctx.place:
            return ctx.place.name
        if ctx.venue_detail:
            return ctx.venue_detail.name
        return ""

    @staticmethod
    def _load_google_accessibility(ctx: ToolPipelineContext) -> dict[str, Any] | None:
        raw = ctx.raw_tool_results.get("accessibility_google")
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    @classmethod
    def _merge_with_google(cls, info, google_accessibility: dict[str, Any] | None):
        if not google_accessibility:
            return info

        merged = info.model_copy(deep=True)
        normalized = google_accessibility.get("normalized")
        if not isinstance(normalized, dict):
            return merged

        if merged.wheelchair_accessible_entrance is None:
            merged.wheelchair_accessible_entrance = cls._as_bool(normalized.get("wheelchair_accessible_entrance"))
        if merged.wheelchair_accessible_parking is None:
            merged.wheelchair_accessible_parking = cls._as_bool(normalized.get("wheelchair_accessible_parking"))
        if merged.wheelchair_accessible_restroom is None:
            merged.wheelchair_accessible_restroom = cls._as_bool(normalized.get("wheelchair_accessible_restroom"))
        if merged.wheelchair_accessible_seating is None:
            merged.wheelchair_accessible_seating = cls._as_bool(normalized.get("wheelchair_accessible_seating"))

        if merged.accessibility_level in ("unknown", "general"):
            level = google_accessibility.get("accessibility_level")
            if isinstance(level, str) and level.strip():
                merged.accessibility_level = level.strip()

        if merged.accessibility_score == 0.0:
            score = google_accessibility.get("accessibility_score")
            if isinstance(score, (int, float)):
                merged.accessibility_score = float(score)

        merged.source = f"{merged.source}+google_places"
        return merged

    @classmethod
    def _build_comparison(
        cls,
        google_accessibility: dict[str, Any] | None,
        merged: dict[str, Any],
        provider: dict[str, Any],
        include_provider_raw: bool,
    ) -> dict[str, Any]:
        google_norm = {}
        if isinstance(google_accessibility, dict):
            value = google_accessibility.get("normalized")
            google_norm = value if isinstance(value, dict) else {}

        provider_normalized = provider.get("response_normalized") if isinstance(provider, dict) else None
        if not isinstance(provider_normalized, dict):
            provider_normalized = {}

        provider_has_data = bool(provider_normalized.get("elements_count"))
        if not provider_has_data and isinstance(provider, dict):
            provider_raw = provider.get("response_raw")
            if isinstance(provider_raw, dict):
                raw_elements = provider_raw.get("elements")
                provider_has_data = isinstance(raw_elements, list) and len(raw_elements) > 0
        merged_flags = {
            "wheelchair_accessible_entrance": merged.get("wheelchair_accessible_entrance"),
            "wheelchair_accessible_parking": merged.get("wheelchair_accessible_parking"),
            "wheelchair_accessible_restroom": merged.get("wheelchair_accessible_restroom"),
            "wheelchair_accessible_seating": merged.get("wheelchair_accessible_seating"),
        }

        field_by_field = {}
        conflicts = []
        for key, merged_value in merged_flags.items():
            google_value = google_norm.get(key)
            status = "only_merged"
            if isinstance(google_value, bool):
                status = "match" if google_value == merged_value else "diff"
                if status == "diff":
                    conflicts.append(
                        {
                            "field": key,
                            "google": google_value,
                            "merged": merged_value,
                        }
                    )

            field_by_field[key] = {
                "google": google_value,
                "merged": merged_value,
                "status": status,
            }

        return {
            "google_available": bool(google_norm),
            "provider": provider.get("provider") if isinstance(provider, dict) else None,
            "provider_has_payload": provider_has_data,
            "provider_payload": (
                provider
                if include_provider_raw
                else {
                    "provider": provider.get("provider") if isinstance(provider, dict) else None,
                    "place_name": provider.get("place_name") if isinstance(provider, dict) else None,
                    "place_id": provider.get("place_id") if isinstance(provider, dict) else None,
                    "response_normalized": provider_normalized,
                }
            ),
            "field_by_field": field_by_field,
            "conflicts": conflicts,
        }

    @staticmethod
    def _extract_overpass_normalized(provider: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(provider, dict):
            return None
        normalized = provider.get("response_normalized")
        if not isinstance(normalized, dict):
            return None
        return {
            "provider": provider.get("provider"),
            "place_name": provider.get("place_name"),
            "place_id": provider.get("place_id"),
            "lat": provider.get("lat"),
            "lng": provider.get("lng"),
            "normalized": normalized,
        }

    @staticmethod
    def _as_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        return None
