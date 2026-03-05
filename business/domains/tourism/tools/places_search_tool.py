"""Places search tool using pluggable PlacesServiceInterface."""

import json

import structlog

from shared.interfaces.places_interface import PlacesServiceInterface
from shared.models.tool_models import ToolError, ToolPipelineContext

logger = structlog.get_logger(__name__)


class PlacesSearchTool:
    """Search for places and retrieve venue details via an injected PlacesServiceInterface."""

    def __init__(self, places_service: PlacesServiceInterface):
        self._service = places_service

    async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
        """Search by place name from ctx, populate ctx.place and ctx.venue_detail."""
        query = self._build_query(ctx)
        if not query:
            return ctx

        try:
            candidates = await self._service.text_search(
                query=query,
                location=ctx.place.destination if ctx.place else None,
                language=ctx.language,
                max_results=3,
            )

            if candidates:
                ctx.place = candidates[0]

                if candidates[0].place_id:
                    detail = await self._service.place_details(
                        place_id=candidates[0].place_id,
                        language=ctx.language,
                    )
                    ctx.venue_detail = detail

                ctx.raw_tool_results["venue info"] = json.dumps(
                    [c.model_dump() for c in candidates],
                    ensure_ascii=False,
                )

            logger.info(
                "places_search_complete",
                query=query,
                results=len(candidates),
                source=self._service.get_service_info().get("provider"),
            )

        except Exception as exc:
            logger.warning("places_search_failed", error=str(exc))
            ctx.errors.append(ToolError(source="places_search", message=str(exc)))

        return ctx

    @staticmethod
    def _build_query(ctx: ToolPipelineContext) -> str:
        if ctx.place and ctx.place.name:
            return ctx.place.name
        if ctx.nlu_result and ctx.nlu_result.entities:
            dest = ctx.nlu_result.entities.get("destination", "")
            if dest:
                return dest
        return ctx.user_input
