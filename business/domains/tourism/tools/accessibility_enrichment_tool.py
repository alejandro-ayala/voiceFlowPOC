"""Accessibility enrichment tool using pluggable AccessibilityServiceInterface."""

import json

import structlog

from shared.interfaces.accessibility_interface import AccessibilityServiceInterface
from shared.models.tool_models import ToolError, ToolPipelineContext

logger = structlog.get_logger(__name__)


class AccessibilityEnrichmentTool:
    """Enrich place data with accessibility info via an injected service."""

    def __init__(self, accessibility_service: AccessibilityServiceInterface):
        self._service = accessibility_service

    async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
        """Enrich ctx.place with accessibility data, populate ctx.accessibility."""
        place_name = self._resolve_place_name(ctx)
        if not place_name:
            return ctx

        try:
            info = await self._service.enrich_accessibility(
                place_name=place_name,
                place_id=ctx.place.place_id if ctx.place else None,
                location=ctx.place.destination if ctx.place else None,
                language=ctx.language,
            )

            ctx.accessibility = info
            ctx.raw_tool_results["accessibility"] = json.dumps(
                info.model_dump(),
                ensure_ascii=False,
            )

            logger.info(
                "accessibility_enrichment_complete",
                place=place_name,
                level=info.accessibility_level,
                source=self._service.get_service_info().get("provider"),
            )

        except Exception as exc:
            logger.warning("accessibility_enrichment_failed", error=str(exc))
            ctx.errors.append(ToolError(source="accessibility_enrichment", message=str(exc)))

        return ctx

    @staticmethod
    def _resolve_place_name(ctx: ToolPipelineContext) -> str:
        if ctx.place:
            return ctx.place.name
        if ctx.venue_detail:
            return ctx.venue_detail.name
        return ""
