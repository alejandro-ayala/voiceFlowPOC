"""Accessibility analysis tool for tourism venues."""

import json
from datetime import datetime

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.accessibility_data import (
    ACCESSIBILITY_DB,
    DEFAULT_ACCESSIBILITY,
)

logger = structlog.get_logger(__name__)


class AccessibilityAnalysisTool(BaseTool):
    """Analyze accessibility requirements and provide venue recommendations."""

    name: str = "accessibility_analysis"
    description: str = "Analyze accessibility needs and provide detailed venue accessibility information"

    def _run(self, nlu_result: str) -> str:
        """Analyze accessibility requirements based on NLU results."""
        logger.info("Accessibility Tool: Processing requirements", nlu_input=nlu_result)

        try:
            nlu_data = json.loads(nlu_result)
            destination = nlu_data.get("entities", {}).get("destination", "general")
        except Exception:
            destination = "general"

        venue_data = ACCESSIBILITY_DB.get(destination, DEFAULT_ACCESSIBILITY)

        result = {
            "accessibility_level": venue_data["accessibility_level"],
            "venue_rating": venue_data["venue_rating"],
            "facilities": venue_data["facilities"],
            "warnings": [],
            "accessibility_score": venue_data["accessibility_score"],
            "certification": venue_data["certification"],
            "last_updated": datetime.now().isoformat(),
        }

        logger.info("Accessibility Tool: Analysis complete", result=result)
        return json.dumps(result, indent=2, ensure_ascii=False)

    async def _arun(self, nlu_result: str) -> str:
        """Async version of accessibility analysis."""
        return self._run(nlu_result)
