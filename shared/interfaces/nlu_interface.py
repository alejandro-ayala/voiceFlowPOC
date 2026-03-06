"""NLU service interface contract for intent classification and entity extraction."""

from abc import ABC, abstractmethod
from typing import Optional

from shared.models.nlu_models import NLUResult


class NLUServiceInterface(ABC):
    """Contract for NLU services: intent classification + slot extraction."""

    @abstractmethod
    async def analyze_text(
        self,
        text: str,
        language: Optional[str] = None,
        profile_context: Optional[dict] = None,
    ) -> NLUResult:
        """Classify intent and extract business entities from text."""
        ...

    @abstractmethod
    def is_service_available(self) -> bool:
        """Report if the provider is ready (API key set, model loaded, etc.)."""
        ...

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """Return list of language codes this provider can handle."""
        ...

    @abstractmethod
    def get_service_info(self) -> dict:
        """Return provider metadata: name, model, version, status."""
        ...
