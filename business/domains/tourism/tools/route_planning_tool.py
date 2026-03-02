"""Route planning tool for accessible transport in Madrid."""

import json

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.route_data import DEFAULT_ROUTE, ROUTE_DB
from shared.interfaces.tourism_data_provider_interface import TourismDataProviderInterface

logger = structlog.get_logger(__name__)


class RoutePlanningTool(BaseTool):
    """Plan optimal accessible routes using Maps APIs."""

    name: str = "route_planning"
    description: str = "Generate accessible routes with multiple transport options and timing"
    tourism_data_provider: TourismDataProviderInterface | None = None

    def _run(self, accessibility_info: str, profile_context: dict | None = None) -> str:
        """Plan accessible routes based on accessibility requirements."""
        logger.info("Route Planning Tool: Generating routes", accessibility_input=accessibility_info)

        destination = self._extract_destination(accessibility_info)

        accessibility_need = None
        try:
            parsed = json.loads(accessibility_info)
            if isinstance(parsed, dict):
                accessibility_need = parsed.get("accessibility_need")
        except Exception:
            accessibility_need = None

        if self.tourism_data_provider is not None and self.tourism_data_provider.is_service_available():
            result = self.tourism_data_provider.plan_routes(
                origin_text=accessibility_info,
                destination=destination,
                accessibility_need=accessibility_need,
                profile_context=profile_context,
                language="es",
            )
            logger.info("Route Planning Tool: Provider routes generated", result=result)
            return json.dumps(result, indent=2, ensure_ascii=False)

        route_data = ROUTE_DB.get(destination, DEFAULT_ROUTE)

        result = {
            "status": "fallback",
            "destination": destination,
            "routes": route_data["routes"],
            "alternatives": [
                "accessible_taxi",
                "uber_wam",
                "accessible_private_transport",
            ],
            "accessibility_score": 8.5,
            "weather_considerations": "Check weather for walking portions",
            "estimated_cost": route_data["cost"],
        }

        logger.info("Route Planning Tool: Routes generated", result=result)
        return json.dumps(result, indent=2, ensure_ascii=False)

    async def _arun(self, accessibility_info: str, profile_context: dict | None = None) -> str:
        """Async version of route planning."""
        return self._run(accessibility_info, profile_context=profile_context)

    @staticmethod
    def _extract_destination(accessibility_info: str) -> str:
        """Extract destination from previous tool output."""
        destination = "Madrid centro"
        if "Prado" in accessibility_info:
            destination = "Museo del Prado"
        elif "Reina" in accessibility_info:
            destination = "Museo Reina Sofía"
        elif "musical" in accessibility_info or "concierto" in accessibility_info:
            destination = "Espacios musicales"
        elif "restaurante" in accessibility_info:
            destination = "Zona restaurantes"
        return destination
