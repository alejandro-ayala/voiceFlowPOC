"""Route planning tool for accessible transport in Madrid."""

import json

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.route_data import DEFAULT_ROUTE, ROUTE_DB

logger = structlog.get_logger(__name__)


class RoutePlanningTool(BaseTool):
    """Plan optimal accessible routes using Maps APIs."""

    name: str = "route_planning"
    description: str = "Generate accessible routes with multiple transport options and timing"

    def _run(self, accessibility_info: str) -> str:
        """Plan accessible routes based on accessibility requirements."""
        logger.info("Route Planning Tool: Generating routes", accessibility_input=accessibility_info)

        destination = self._extract_destination(accessibility_info)
        route_data = ROUTE_DB.get(destination, DEFAULT_ROUTE)

        result = {
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

    async def _arun(self, accessibility_info: str) -> str:
        """Async version of route planning."""
        return self._run(accessibility_info)

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
