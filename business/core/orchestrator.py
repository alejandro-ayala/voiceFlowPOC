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
            exec_result = self._execute_pipeline(user_input)

            # _execute_pipeline may return either tool_results (dict) or (tool_results, metadata)
            if isinstance(exec_result, tuple) and len(exec_result) == 2:
                tool_results, metadata = exec_result
            else:
                tool_results = exec_result
                metadata = {}

            prompt = self._build_response_prompt(user_input, tool_results)

            # Measure LLM invocation time
            import time

            llm_start = time.perf_counter()
            response = self.llm.invoke(prompt)
            llm_end = time.perf_counter()
            llm_duration_ms = int((llm_end - llm_start) * 1000)

            text = response.content if hasattr(response, "content") else str(response)

            # Allow subclasses to extract structured data from LLM output
            text, metadata = self._extract_structured_data(text, metadata)

            # Append LLM step to pipeline_steps in metadata
            pipeline_steps = metadata.get("pipeline_steps") if isinstance(metadata, dict) else None
            if pipeline_steps is None:
                pipeline_steps = []
                metadata["pipeline_steps"] = pipeline_steps

            pipeline_steps.append(
                {
                    "name": "Response",
                    "tool": "llm_synthesis",
                    "status": "completed",
                    "duration_ms": llm_duration_ms,
                    "summary": (text[:200] if text else ""),
                }
            )

            self.conversation_history.append({"user": user_input, "assistant": text})
            logger.info("Request processed successfully", response_length=len(text))
            return AgentResponse(response_text=text, tool_results=tool_results, metadata=metadata)
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

    def _extract_structured_data(self, llm_text: str, metadata: dict) -> tuple[str, dict]:
        """Hook for subclasses to extract structured data from LLM response.

        Override this to parse structured output (e.g. JSON blocks) from the
        LLM text and merge it into metadata. The returned text should have
        the structured block removed so only conversational content remains.

        Returns:
            (clean_text, updated_metadata)
        """
        return llm_text, metadata
