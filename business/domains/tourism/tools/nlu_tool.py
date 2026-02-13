"""NLU tool for extracting intents and entities from Spanish tourism requests."""

import json
from datetime import datetime

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.nlu_patterns import (
    ACCESSIBILITY_PATTERNS,
    DESTINATION_PATTERNS,
    INTENT_PATTERNS,
    MADRID_GENERAL_KEYWORDS,
    MADRID_SPECIFIC_EXCLUSIONS,
)

logger = structlog.get_logger(__name__)


class TourismNLUTool(BaseTool):
    """Extract intents and entities from Spanish tourism requests."""

    name: str = "tourism_nlu"
    description: str = "Analyze user intent and extract tourism entities from Spanish text"

    def _run(self, user_input: str) -> str:
        """Analyze Spanish tourism request and extract structured information."""
        logger.info("NLU Tool: Processing user input", input=user_input)

        user_lower = user_input.lower()

        intent = self._match_pattern(user_lower, INTENT_PATTERNS, "information_request")
        destination = self._extract_destination(user_lower)
        accessibility = self._match_pattern(user_lower, ACCESSIBILITY_PATTERNS, "general")

        result = {
            "intent": intent,
            "entities": {
                "destination": destination,
                "accessibility": accessibility,
                "language": "spanish",
            },
            "confidence": 0.85,
            "timestamp": datetime.now().isoformat(),
            "analysis": f"Detected {intent} for {destination} with {accessibility} accessibility needs",
        }

        logger.info("NLU Tool: Analysis complete", result=result)
        return json.dumps(result, indent=2, ensure_ascii=False)

    async def _arun(self, user_input: str) -> str:
        """Async version of NLU processing."""
        return self._run(user_input)

    @staticmethod
    def _match_pattern(text: str, patterns: dict[str, list[str]], default: str) -> str:
        """Match text against keyword patterns, return first match or default."""
        for name, keywords in patterns.items():
            if any(kw in text for kw in keywords):
                return name
        return default

    @staticmethod
    def _extract_destination(text: str) -> str:
        """Extract destination with special handling for generic 'madrid' queries."""
        for dest_name, keywords in DESTINATION_PATTERNS.items():
            if any(kw in text for kw in keywords):
                return dest_name

        # Check for generic "madrid" without specific venue
        if any(kw in text for kw in MADRID_GENERAL_KEYWORDS):
            if not any(specific in text for specific in MADRID_SPECIFIC_EXCLUSIONS):
                return "Madrid centro"

        return "general"
