"""spaCy implementation for pluggable NER location extraction."""

import asyncio
from typing import Any, Dict, Optional

import structlog

from integration.configuration.settings import Settings, get_ner_model_map
from shared.interfaces.ner_interface import NERServiceInterface

logger = structlog.get_logger(__name__)

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    spacy = None
    SPACY_AVAILABLE = False


class SpacyNERService(NERServiceInterface):
    """NER service backed by spaCy models configured by language."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or Settings()
        self._provider_name = "spacy"
        self._model_map = get_ner_model_map(self._settings.ner_model_map)
        self._model_cache: dict[str, Any] = {}
        self._default_language = self._settings.ner_default_language.lower()
        self._fallback_model = self._settings.ner_fallback_model

        if not SPACY_AVAILABLE:
            logger.warning("spaCy is not installed; NER provider unavailable")

    async def extract_locations(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Extract location entities (GPE/LOC/FAC) from input text."""
        if not text or not text.strip():
            return {
                "locations": [],
                "top_location": None,
                "language": (language or self._default_language),
                "provider": self._provider_name,
                "model": None,
                "status": "empty_input",
            }

        selected_language = (language or self._default_language).lower()

        if not self.is_service_available():
            return {
                "locations": [],
                "top_location": None,
                "language": selected_language,
                "provider": self._provider_name,
                "model": None,
                "status": "provider_unavailable",
            }

        model_name = self._resolve_model_for_language(selected_language)
        nlp = self._load_model(model_name, selected_language)

        if nlp is None:
            return {
                "locations": [],
                "top_location": None,
                "language": selected_language,
                "provider": self._provider_name,
                "model": model_name,
                "status": "model_unavailable",
            }

        loop = asyncio.get_running_loop()
        doc = await loop.run_in_executor(None, nlp, text)

        allowed_labels = {"LOC", "GPE", "FAC"}
        extracted_locations: list[str] = []
        seen: set[str] = set()
        for entity in doc.ents:
            if entity.label_ not in allowed_labels:
                continue
            value = entity.text.strip()
            key = value.lower()
            if value and key not in seen:
                seen.add(key)
                extracted_locations.append(value)

        return {
            "locations": extracted_locations,
            "top_location": extracted_locations[0] if extracted_locations else None,
            "language": selected_language,
            "provider": self._provider_name,
            "model": model_name,
            "status": "ok",
            "count": len(extracted_locations),
        }

    def is_service_available(self) -> bool:
        """Return True when spaCy dependency is installed and NER is enabled."""
        return SPACY_AVAILABLE and self._settings.ner_enabled

    def get_supported_languages(self) -> list[str]:
        """Return supported language codes from configured model map."""
        return sorted(self._model_map.keys())

    def get_service_info(self) -> Dict[str, Any]:
        """Return provider metadata and runtime status."""
        return {
            "provider": self._provider_name,
            "available": self.is_service_available(),
            "default_language": self._default_language,
            "model_map": self._model_map,
            "fallback_model": self._fallback_model,
            "cached_models": sorted(self._model_cache.keys()),
        }

    def _resolve_model_for_language(self, language: str) -> str:
        """Resolve model name for language, fallback to default language mapping."""
        return self._model_map.get(language) or self._model_map.get(self._default_language) or self._fallback_model

    def _load_model(self, model_name: str, language: str) -> Any:
        """Load and cache spaCy model; fallback to configured fallback model if needed."""
        cache_key = f"{language}:{model_name}"
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        try:
            model = spacy.load(model_name)
            self._model_cache[cache_key] = model
            return model
        except Exception as error:
            logger.warning(
                "Failed to load configured spaCy model",
                language=language,
                model=model_name,
                error=str(error),
            )

            if model_name == self._fallback_model:
                return None

            try:
                fallback_key = f"{language}:{self._fallback_model}"
                if fallback_key in self._model_cache:
                    return self._model_cache[fallback_key]

                fallback_model = spacy.load(self._fallback_model)
                self._model_cache[fallback_key] = fallback_model
                return fallback_model
            except Exception as fallback_error:
                logger.error(
                    "Failed to load fallback spaCy model",
                    language=language,
                    fallback_model=self._fallback_model,
                    error=str(fallback_error),
                )
                return None
