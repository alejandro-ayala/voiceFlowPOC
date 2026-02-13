"""Tourism information tool for venue details, schedules, and pricing."""

import json
from datetime import datetime

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.venue_data import DEFAULT_VENUE, VENUE_DB

logger = structlog.get_logger(__name__)


class TourismInfoTool(BaseTool):
    """Get real-time tourism information and reviews."""

    name: str = "tourism_info"
    description: str = "Fetch current tourism information, schedules, prices, and accessibility reviews"

    def _run(self, venue_info: str) -> str:
        """Get comprehensive tourism information."""
        logger.info("Tourism Info Tool: Fetching venue information", venue_input=venue_info)

        venue_name = self._extract_venue_name(venue_info)
        venue_data = VENUE_DB.get(venue_name, DEFAULT_VENUE)

        result = {
            "venue": venue_name,
            "opening_hours": venue_data["opening_hours"],
            "pricing": venue_data["pricing"],
            "accessibility_reviews": venue_data["accessibility_reviews"],
            "current_crowds": "moderate",
            "special_exhibitions": venue_data["special_exhibitions"],
            "accessibility_services": venue_data["accessibility_services"],
            "contact": venue_data["contact"],
            "last_updated": datetime.now().isoformat(),
        }

        logger.info("Tourism Info Tool: Information retrieved", result=result)
        return json.dumps(result, indent=2, ensure_ascii=False)

    async def _arun(self, venue_info: str) -> str:
        """Async version of tourism info retrieval."""
        return self._run(venue_info)

    @staticmethod
    def _extract_venue_name(venue_info: str) -> str:
        """Extract venue name from input text."""
        venue_lower = venue_info.lower()

        if "prado" in venue_lower:
            return "Museo del Prado"
        elif "reina" in venue_lower:
            return "Museo Reina Sofía"
        elif "thyssen" in venue_lower:
            return "Museo Thyssen"
        elif "musical" in venue_lower or "concierto" in venue_lower:
            return "Espacios musicales Madrid"
        elif "restaurante" in venue_lower:
            return "Restaurantes accesibles Madrid"
        elif "parque" in venue_lower or "retiro" in venue_lower:
            return "Parques Madrid"

        return "General Madrid"
