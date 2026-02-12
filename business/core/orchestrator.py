"""Base orchestrator for multi-agent LLM systems (Template Method pattern)."""

import asyncio
from abc import abstractmethod
from typing import Any

import structlog

from business.core.interfaces import MultiAgentInterface
from business.core.models import AgentResponse

logger = structlog.get_logger(__name__)


class MultiAgentOrchestrator(MultiAgentInterface):
    """
    Base orchestrator for LLM multi-agent systems.

    Provides reusable logic for:
    - LLM invocation with prompts built from tool results
    - Conversation history management
    - Sync/async wrappers

    Subclasses must implement:
    - _execute_pipeline(): Which tools to run and how to chain them
    - _build_response_prompt(): How to build the synthesis prompt for the LLM
    """

    def __init__(self, llm: Any, system_prompt: str):
        self.llm = llm
        self.system_prompt = system_prompt
        self.conversation_history: list[dict[str, str]] = []

    def process_request_sync(self, user_input: str) -> AgentResponse:
        """Execute tool pipeline + LLM synchronously."""
        try:
            logger.info("Processing request", input=user_input)
            tool_results = self._execute_pipeline(user_input)
            prompt = self._build_response_prompt(user_input, tool_results)
            response = self.llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            self.conversation_history.append({"user": user_input, "assistant": text})
            logger.info("Request processed successfully", response_length=len(text))
            return AgentResponse(response_text=text, tool_results=tool_results)
        except Exception as e:
            logger.error("Error processing request", error=str(e))
            error_text = f"Lo siento, hubo un error procesando tu solicitud: {str(e)}"
            return AgentResponse(response_text=error_text, tool_results={})

    async def process_request(self, user_input: str) -> AgentResponse:
        """Execute tool pipeline + LLM asynchronously (runs sync in thread)."""
        return await asyncio.to_thread(self.process_request_sync, user_input)

    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Return conversation history."""
        return [{"user": m["user"], "assistant": m["assistant"]} for m in self.conversation_history]

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    @abstractmethod
    def _execute_pipeline(self, user_input: str) -> dict[str, str]:
        """Execute domain tools. Return {tool_name: json_result_string}."""
        ...

    @abstractmethod
    def _build_response_prompt(self, user_input: str, tool_results: dict[str, str]) -> str:
        """Build the final prompt for LLM synthesis from tool results."""
        ...
