"""NER service interface for pluggable location extraction providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class NERServiceInterface(ABC):
    """Contract for Named Entity Recognition services focused on locations."""

    @abstractmethod
    async def extract_locations(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Extract location entities (LOC/GPE-like) from free text."""
        pass

    @abstractmethod
    def is_service_available(self) -> bool:
        """Report if the NER provider is ready to process requests."""
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return configured/supported language codes for NER extraction."""
        pass

    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """Return provider metadata (name, model mapping, status)."""
        pass
