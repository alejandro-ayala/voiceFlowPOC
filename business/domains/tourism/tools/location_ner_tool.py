"""Location Named Entity Recognition Tool for tourism domain using spaCy NER service."""

import asyncio
import json
import time
from typing import Optional

import structlog
from langchain.tools import BaseTool

from integration.external_apis.ner_factory import NERServiceFactory
from shared.interfaces.ner_interface import NERServiceInterface

logger = structlog.get_logger(__name__)


class LocationNERTool(BaseTool):
    """Extract location entities from user input using NER service (spaCy-based)."""

    name: str = "location_ner"
    description: str = "Extract location entities (venues, cities, points of interest) using Named Entity Recognition"
    ner_service: Optional[NERServiceInterface] = None

    def _get_ner_service(self) -> NERServiceInterface:
        """Return injected NER service or create one from settings."""
        if self.ner_service is not None:
            return self.ner_service
        return NERServiceFactory.create_from_settings()

    def _run(self, user_input: str, language: str = "es") -> str:
        """Extract locations from user input using NER service.

        Args:
            user_input: User text (typically from NLU output or raw input)
            language: Language code (default: "es" for Spanish)

        Returns:
            JSON string with extracted locations, top_location, provider info, and status
        """
        logger.info("LocationNERTool: Processing user input", input=user_input, language=language)
        start = time.perf_counter()

        try:
            ner_service = self._get_ner_service()

            # Check if NER is available
            if not ner_service.is_service_available():
                logger.warning("LocationNERTool: NER service not available, returning empty result")
                return json.dumps(
                    {
                        "locations": [],
                        "top_location": None,
                        "provider": "spacy",
                        "model": "not_available",
                        "language": language,
                        "status": "unavailable",
                        "reason": "NER service not available",
                    },
                    ensure_ascii=False,
                )

            # Run NER extraction asynchronously
            result = asyncio.run(ner_service.extract_locations(text=user_input, language=language))

            # Normalize result to expected schema
            response = {
                "locations": result.get("locations", []),
                "top_location": result.get("top_location"),
                "provider": result.get("provider", "spacy"),
                "model": result.get("model", "unknown"),
                "language": result.get("language", language),
                "status": result.get("status", "ok"),
            }

            logger.info(
                "location_ner_tool_result",
                provider=response.get("provider"),
                model=response.get("model"),
                language=response.get("language"),
                latency_ms=int((time.perf_counter() - start) * 1000),
                location_count=len(response.get("locations", [])),
                status=response.get("status"),
            )

            return json.dumps(response, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error("LocationNERTool: Error during NER extraction", error=str(e), exc_info=True)
            return json.dumps(
                {
                    "locations": [],
                    "top_location": None,
                    "provider": "spacy",
                    "model": "error",
                    "language": language,
                    "status": "error",
                    "reason": str(e),
                },
                ensure_ascii=False,
            )

    async def _arun(self, user_input: str, language: str = "es") -> str:
        """Async version of location NER extraction."""
        logger.info("LocationNERTool: Async processing user input", input=user_input, language=language)
        start = time.perf_counter()

        try:
            ner_service = self._get_ner_service()

            # Check if NER is available
            if not ner_service.is_service_available():
                logger.warning("LocationNERTool: NER service not available (async), returning empty result")
                return json.dumps(
                    {
                        "locations": [],
                        "top_location": None,
                        "provider": "spacy",
                        "model": "not_available",
                        "language": language,
                        "status": "unavailable",
                        "reason": "NER service not available",
                    },
                    ensure_ascii=False,
                )

            # Run NER extraction asynchronously
            result = await ner_service.extract_locations(text=user_input, language=language)

            # Normalize result to expected schema
            response = {
                "locations": result.get("locations", []),
                "top_location": result.get("top_location"),
                "provider": result.get("provider", "spacy"),
                "model": result.get("model", "unknown"),
                "language": result.get("language", language),
                "status": result.get("status", "ok"),
            }

            logger.info(
                "location_ner_tool_result",
                provider=response.get("provider"),
                model=response.get("model"),
                language=response.get("language"),
                latency_ms=int((time.perf_counter() - start) * 1000),
                location_count=len(response.get("locations", [])),
                status=response.get("status"),
            )

            return json.dumps(response, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error("LocationNERTool: Error during async NER extraction", error=str(e), exc_info=True)
            return json.dumps(
                {
                    "locations": [],
                    "top_location": None,
                    "provider": "spacy",
                    "model": "error",
                    "language": language,
                    "status": "error",
                    "reason": str(e),
                },
                ensure_ascii=False,
            )
