"""Core framework for multi-agent LLM orchestration (reusable across projects)."""

from business.core.interfaces import MultiAgentInterface
from business.core.models import AgentResponse
from business.core.orchestrator import MultiAgentOrchestrator

__all__ = ["MultiAgentInterface", "AgentResponse", "MultiAgentOrchestrator"]
