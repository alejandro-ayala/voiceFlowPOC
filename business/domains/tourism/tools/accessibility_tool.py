"""Accessibility analysis tool for tourism venues."""

import json
from datetime import datetime

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.accessibility_data import (
    ACCESSIBILITY_DB,
    DEFAULT_ACCESSIBILITY,
)
from business.domains.tourism.profile_matcher import ProfileMatcher
from shared.interfaces.tourism_data_provider_interface import TourismDataProviderInterface

logger = structlog.get_logger(__name__)


class AccessibilityAnalysisTool(BaseTool):
    """Analyze accessibility requirements and provide venue recommendations."""

    name: str = "accessibility_analysis"
    description: str = "Analyze accessibility needs and provide detailed venue accessibility information"
    tourism_data_provider: TourismDataProviderInterface | None = None

    def _run(self, nlu_result: str, profile_context: dict | None = None) -> str:
        """Analyze accessibility requirements based on NLU results."""
        logger.info("Accessibility Tool: Processing requirements", nlu_input=nlu_result)

        try:
            nlu_data = json.loads(nlu_result)
            destination = nlu_data.get("entities", {}).get("destination", "general")
            accessibility_need = nlu_data.get("entities", {}).get("accessibility")
        except Exception:
            destination = "general"
            accessibility_need = None

        if self.tourism_data_provider is not None and self.tourism_data_provider.is_service_available():
            result = self.tourism_data_provider.get_accessibility_insights(
                destination=destination,
                accessibility_need=accessibility_need,
                profile_context=profile_context,
                language="es",
            )
            logger.info("Accessibility Tool: Provider analysis complete", result=result)
            return json.dumps(result, indent=2, ensure_ascii=False)

        venue_data = ACCESSIBILITY_DB.get(destination, DEFAULT_ACCESSIBILITY)

        profile_match = ProfileMatcher.build_accessibility_match(
            profile_context=profile_context,
            facilities=venue_data.get("facilities", []),
            accessibility_need=accessibility_need,
        )

        result = {
            "status": "fallback",
            "destination": destination,
            "accessibility_level": venue_data["accessibility_level"],
            "venue_rating": venue_data["venue_rating"],
            "facilities": venue_data["facilities"],
            "warnings": [],
            "accessibility_score": venue_data["accessibility_score"],
            "certification": venue_data["certification"],
            "profile_accessibility_match": profile_match,
            "last_updated": datetime.now().isoformat(),
        }

        logger.info("Accessibility Tool: Analysis complete", result=result)
        return json.dumps(result, indent=2, ensure_ascii=False)

    async def _arun(self, nlu_result: str, profile_context: dict | None = None) -> str:
        """Async version of accessibility analysis."""
        return self._run(nlu_result, profile_context=profile_context)
