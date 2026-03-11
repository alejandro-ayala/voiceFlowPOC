"""Directions tool using pluggable DirectionsServiceInterface."""

import json

import structlog

from shared.interfaces.directions_interface import DirectionsServiceInterface
from shared.models.tool_models import ToolError, ToolPipelineContext

logger = structlog.get_logger(__name__)


class DirectionsTool:
    """Compute accessible routes via an injected DirectionsServiceInterface."""

    def __init__(self, directions_service: DirectionsServiceInterface):
        self._service = directions_service

    async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
        """Compute routes to ctx.place, populate ctx.routes."""
        destination = self._resolve_destination(ctx)
        if not destination:
            return ctx

        origin = self._resolve_origin(ctx)
        accessibility_profile = self._resolve_profile(ctx)

        try:
            routes = await self._service.get_directions(
                origin=origin,
                destination=destination,
                mode="transit",
                accessibility_profile=accessibility_profile,
                language=ctx.language,
            )

            ctx.routes = routes
            ctx.raw_tool_results["routes"] = json.dumps(
                [r.model_dump() for r in routes],
                ensure_ascii=False,
            )

            logger.info(
                "directions_complete",
                destination=destination,
                routes_count=len(routes),
                source=self._service.get_service_info().get("provider"),
            )

        except Exception as exc:
            logger.warning("directions_failed", error=str(exc))
            ctx.errors.append(ToolError(source="directions", message=str(exc)))

        return ctx

    @staticmethod
    def _resolve_destination(ctx: ToolPipelineContext) -> str:
        if ctx.place:
            addr = ctx.place.address or ctx.place.name
            return addr
        if ctx.venue_detail:
            return ctx.venue_detail.name
        return ""

    @staticmethod
    def _resolve_origin(ctx: ToolPipelineContext) -> str:
        if ctx.profile_context:
            coords = ctx.profile_context.get("location_coordinates")
            if isinstance(coords, dict):
                lat = coords.get("latitude")
                lng = coords.get("longitude")
                try:
                    return f"{float(lat):.6f},{float(lng):.6f}"
                except (TypeError, ValueError):
                    pass

            location = ctx.profile_context.get("location")
            if isinstance(location, str) and location.strip():
                return location.strip()
        return "Madrid centro"

    @staticmethod
    def _resolve_profile(ctx: ToolPipelineContext) -> str | None:
        if ctx.profile_context:
            needs = ctx.profile_context.get("accessibility_needs", [])
            if isinstance(needs, list) and "wheelchair" in needs:
                return "wheelchair"
        return None
