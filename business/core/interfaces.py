"""Generic interface for multi-agent LLM systems."""

from abc import ABC, abstractmethod
from typing import Any

from business.core.models import AgentResponse


class MultiAgentInterface(ABC):
    """Contract for any LLM-based multi-agent system.

    Implementations define domain-specific tool pipelines and prompts
    while inheriting common orchestration logic from MultiAgentOrchestrator.
    """

    @abstractmethod
    def process_request_sync(self, user_input: str) -> AgentResponse:
        """Process a query synchronously through the tool pipeline + LLM."""
        ...

    @abstractmethod
    async def process_request(self, user_input: str) -> AgentResponse:
        """Process a query asynchronously (async wrapper over sync)."""
        ...

    @abstractmethod
    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Return conversation history as list of {user, assistant} dicts."""
        ...

    @abstractmethod
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        ...
