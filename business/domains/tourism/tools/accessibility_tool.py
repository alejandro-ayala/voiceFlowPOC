"""Accessibility analysis tool for tourism venues."""

import json
from datetime import datetime

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.accessibility_data import (
    ACCESSIBILITY_DB,
    DEFAULT_ACCESSIBILITY,
)
from shared.models.tool_models import AccessibilityInfo, ToolPipelineContext

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

    async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
        """Execute with typed pipeline context. Populates ctx.accessibility."""
        nlu_input = ctx.raw_tool_results.get("nlu", "{}")
        raw_result = self._run(nlu_input)
        ctx.raw_tool_results["accessibility"] = raw_result
        try:
            parsed = json.loads(raw_result)
            ctx.accessibility = AccessibilityInfo(
                accessibility_level=parsed.get("accessibility_level", "general"),
                venue_rating=parsed.get("venue_rating"),
                facilities=parsed.get("facilities", []),
                warnings=parsed.get("warnings", []),
                accessibility_score=parsed.get("accessibility_score", 0.0),
                certification=parsed.get("certification"),
                source="local_db",
            )
        except Exception as e:
            logger.warning("Failed to parse accessibility result", error=str(e))
        return ctx
