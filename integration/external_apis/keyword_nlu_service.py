"""Keyword-based NLU fallback provider."""

from __future__ import annotations

from typing import Optional

from business.domains.tourism.data.nlu_patterns import (
    ACCESSIBILITY_PATTERNS,
    DESTINATION_PATTERNS,
    INTENT_PATTERNS,
    MADRID_GENERAL_KEYWORDS,
    MADRID_SPECIFIC_EXCLUSIONS,
)
from integration.configuration.settings import Settings
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUEntitySet, NLUResult


class KeywordNLUService(NLUServiceInterface):
    """Fallback NLU using deterministic keyword matching."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or Settings()
        self._provider_name = "keyword"
        self._default_language = self._settings.nlu_default_language

    async def analyze_text(
        self,
        text: str,
        language: Optional[str] = None,
        profile_context: Optional[dict] = None,
    ) -> NLUResult:
        del profile_context

        selected_language = language or self._default_language
        text_lower = text.lower() if text else ""

        intent = self._match_intent(text_lower)
        destination = self._extract_destination(text_lower)
        accessibility = self._match_pattern(text_lower, ACCESSIBILITY_PATTERNS)

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
            provider=self._provider_name,
            model="keyword_patterns",
            language=selected_language,
        )

    def is_service_available(self) -> bool:
        return self._settings.nlu_enabled

    def get_supported_languages(self) -> list[str]:
        return ["es"]

    def get_service_info(self) -> dict:
        return {
            "provider": self._provider_name,
            "model": "keyword_patterns",
            "available": self.is_service_available(),
            "default_language": self._default_language,
            "classification_method": "keyword_matching",
            "analysis_version": "nlu_v3.0",
        }

    @staticmethod
    def _match_pattern(text: str, patterns: dict[str, list[str]]) -> str | None:
        for label, keywords in patterns.items():
            if any(keyword in text for keyword in keywords):
                return label
        return None

    @staticmethod
    def _match_intent(text: str) -> str:
        for intent, keywords in INTENT_PATTERNS.items():
            if any(keyword in text for keyword in keywords):
                return intent
        return "general_query"

    @staticmethod
    def _extract_destination(text: str) -> str | None:
        for destination, keywords in DESTINATION_PATTERNS.items():
            if any(keyword in text for keyword in keywords):
                return destination

        if any(keyword in text for keyword in MADRID_GENERAL_KEYWORDS):
            if not any(specific in text for specific in MADRID_SPECIFIC_EXCLUSIONS):
                return "Madrid centro"

        return None
