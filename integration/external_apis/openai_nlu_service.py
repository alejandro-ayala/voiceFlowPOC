"""OpenAI NLU provider using function calling for intent and entity extraction."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

import structlog
from openai import AsyncOpenAI

from integration.configuration.settings import Settings
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUAlternative, NLUEntitySet, NLUResult

logger = structlog.get_logger(__name__)

NLU_FUNCTION_SCHEMA = {
    "name": "classify_tourism_request",
    "description": "Classify a tourism user request into intent and extract entities",
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "route_planning",
                    "event_search",
                    "restaurant_search",
                    "accommodation_search",
                    "general_query",
                ],
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "destination": {
                "type": "string",
                "nullable": True,
            },
            "accessibility": {
                "type": "string",
                "enum": ["wheelchair", "visual_impairment", "hearing_impairment", "cognitive"],
                "nullable": True,
            },
            "timeframe": {
                "type": "string",
                "enum": ["today", "today_morning", "today_afternoon", "today_evening", "tomorrow", "this_weekend"],
                "nullable": True,
            },
            "transport_preference": {
                "type": "string",
                "enum": ["metro", "bus", "walk", "taxi"],
                "nullable": True,
            },
            "alternative_intent": {
                "type": "string",
                "enum": [
                    "route_planning",
                    "event_search",
                    "restaurant_search",
                    "accommodation_search",
                    "general_query",
                ],
                "nullable": True,
            },
            "alternative_confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "nullable": True,
            },
        },
        "required": ["intent", "confidence"],
    },
}

NLU_SYSTEM_PROMPT = (
    "You are an NLU classifier for an accessible tourism assistant focused on Spain. "
    "Classify the user's intent and extract relevant entities. "
    "Detect accessibility needs even when expressed indirectly. "
    "The user may write in Spanish or English."
)


class OpenAINLUService(NLUServiceInterface):
    """NLU provider using OpenAI function calling."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or Settings()
        self._provider_name = "openai"
        self._model = self._settings.nlu_openai_model
        self._default_language = self._settings.nlu_default_language

        api_key = self._settings.openai_api_key
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None

        if self._client is None:
            logger.warning("openai_nlu_provider_unavailable_no_api_key")

    async def analyze_text(
        self,
        text: str,
        language: Optional[str] = None,
        profile_context: Optional[dict] = None,
    ) -> NLUResult:
        """Classify intent and extract entities via OpenAI function calling."""
        del profile_context

        selected_language = language or self._default_language

        if not text or not text.strip():
            return NLUResult(
                status="error",
                provider=self._provider_name,
                model=self._model,
                language=selected_language,
            )

        if not self.is_service_available():
            return NLUResult(
                status="error",
                provider=self._provider_name,
                model=self._model,
                language=selected_language,
            )

        start = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": NLU_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                tools=[{"type": "function", "function": NLU_FUNCTION_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "classify_tourism_request"}},
            )

            latency_ms = int((time.perf_counter() - start) * 1000)

            tool_call = response.choices[0].message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)

            alternatives: list[NLUAlternative] = []
            alt_intent = args.get("alternative_intent")
            alt_confidence = args.get("alternative_confidence")
            if alt_intent and alt_confidence is not None:
                alternatives.append(NLUAlternative(intent=alt_intent, confidence=alt_confidence))

            result = NLUResult(
                status="ok",
                intent=args.get("intent", "general_query"),
                confidence=args.get("confidence", 0.0),
                entities=NLUEntitySet(
                    destination=args.get("destination"),
                    accessibility=args.get("accessibility"),
                    timeframe=args.get("timeframe"),
                    transport_preference=args.get("transport_preference"),
                ),
                alternatives=alternatives,
                provider=self._provider_name,
                model=self._model,
                language=selected_language,
                latency_ms=latency_ms,
            )

            logger.info(
                "nlu_analysis_complete",
                provider=result.provider,
                model=result.model,
                intent=result.intent,
                confidence=result.confidence,
                status=result.status,
                latency_ms=result.latency_ms,
                classification_layer="openai_function_calling",
            )
            return result

        except Exception as error:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.error("openai_nlu_error", error=str(error), latency_ms=latency_ms)
            return NLUResult(
                status="error",
                provider=self._provider_name,
                model=self._model,
                language=selected_language,
                latency_ms=latency_ms,
            )

    def is_service_available(self) -> bool:
        return self._client is not None and self._settings.nlu_enabled

    def get_supported_languages(self) -> list[str]:
        return ["es", "en", "fr", "de", "it", "pt", "ca", "eu", "gl"]

    def get_service_info(self) -> dict[str, Any]:
        return {
            "provider": self._provider_name,
            "model": self._model,
            "available": self.is_service_available(),
            "default_language": self._default_language,
            "classification_method": "function_calling",
            "analysis_version": "nlu_v3.0",
        }
