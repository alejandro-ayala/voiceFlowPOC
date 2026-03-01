"""NLU tool for extracting intents and entities from Spanish tourism requests."""

import asyncio
import json
from datetime import datetime
from typing import Optional

import structlog
from langchain.tools import BaseTool

from business.domains.tourism.data.nlu_patterns import (
    ACCESSIBILITY_PATTERNS,
    DESTINATION_PATTERNS,
    INTENT_PATTERNS,
    MADRID_GENERAL_KEYWORDS,
    MADRID_SPECIFIC_EXCLUSIONS,
)
from integration.external_apis.nlu_factory import NLUServiceFactory
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUEntitySet, NLUResult

logger = structlog.get_logger(__name__)


class TourismNLUTool(BaseTool):
    """Extract intents and entities from Spanish tourism requests."""

    name: str = "tourism_nlu"
    description: str = "Analyze user intent and extract tourism entities from Spanish text"
    nlu_service: Optional[NLUServiceInterface] = None

    def _get_nlu_service(self) -> NLUServiceInterface:
        if self.nlu_service is not None:
            return self.nlu_service
        return NLUServiceFactory.create_from_settings()

    def _legacy_result(self, user_input: str, language: str = "es") -> NLUResult:
        user_lower = user_input.lower()

        intent = self._match_pattern(user_lower, INTENT_PATTERNS, "general_query")
        destination = self._extract_destination(user_lower)
        accessibility = self._match_pattern(user_lower, ACCESSIBILITY_PATTERNS, "general")

        confidence = 0.70 if intent != "general_query" else 0.0
        status = "ok" if intent != "general_query" else "fallback"

        return NLUResult(
            status=status,
            intent=intent,
            confidence=confidence,
            entities=NLUEntitySet(
                destination=destination,
                accessibility=accessibility,
            ),
            provider="keyword",
            model="keyword_patterns",
            language=language,
        )

    @staticmethod
    def _to_payload(result: NLUResult) -> dict:
        destination = result.entities.destination or "general"
        accessibility = result.entities.accessibility or "general"
        return {
            "intent": result.intent,
            "entities": {
                "destination": destination,
                "accessibility": accessibility,
                "language": result.language,
            },
            "confidence": result.confidence,
            "status": result.status,
            "provider": result.provider,
            "model": result.model,
            "analysis_version": result.analysis_version,
            "latency_ms": result.latency_ms,
            "alternatives": [alt.model_dump() for alt in result.alternatives],
            "timestamp": datetime.now().isoformat(),
            "analysis": f"Detected {result.intent} for {destination} with {accessibility} accessibility needs",
        }

    async def _analyze(self, user_input: str, language: str = "es") -> NLUResult:
        service = self._get_nlu_service()
        if not service.is_service_available():
            logger.warning("nlu_service_unavailable_using_keyword_fallback")
            return self._legacy_result(user_input, language=language)

        try:
            result = await service.analyze_text(user_input, language=language)
            if result.status == "error":
                logger.warning("nlu_service_error_using_keyword_fallback")
                return self._legacy_result(user_input, language=language)
            return result
        except Exception as error:
            logger.warning("nlu_service_exception_using_keyword_fallback", error=str(error))
            return self._legacy_result(user_input, language=language)

    def _run(self, user_input: str) -> str:
        """Analyze Spanish tourism request and extract structured information."""
        logger.info("NLU Tool: Processing user input", input=user_input)
        result = asyncio.run(self._analyze(user_input, language="es"))
        payload = self._to_payload(result)
        logger.info("NLU Tool: Analysis complete", result=payload)
        return json.dumps(payload, indent=2, ensure_ascii=False)

    async def _arun(self, user_input: str) -> str:
        """Async version of NLU processing."""
        result = await self._analyze(user_input, language="es")
        payload = self._to_payload(result)
        logger.info("NLU Tool: Analysis complete (async)", result=payload)
        return json.dumps(payload, indent=2, ensure_ascii=False)

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
