"""Tourism domain orchestrator - wires core framework with tourism-specific tools and prompts."""

import os
from typing import Optional

import structlog
from langchain_openai import ChatOpenAI

from business.core.orchestrator import MultiAgentOrchestrator
from business.domains.tourism.prompts.response_prompt import build_response_prompt
from business.domains.tourism.prompts.system_prompt import SYSTEM_PROMPT
from business.domains.tourism.tools.accessibility_tool import AccessibilityAnalysisTool
from business.domains.tourism.tools.nlu_tool import TourismNLUTool
from business.domains.tourism.tools.route_planning_tool import RoutePlanningTool
from business.domains.tourism.tools.tourism_info_tool import TourismInfoTool

logger = structlog.get_logger(__name__)


class TourismMultiAgent(MultiAgentOrchestrator):
    """
    Orchestrator for the accessible tourism domain (Madrid).

    Coordinates 4 specialized tools through a fixed pipeline:
    NLU -> Accessibility -> Route Planning + Tourism Info -> LLM synthesis.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the tourism multi-agent system."""
        logger.info("Initializing Tourism Multi-Agent System")

        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            openai_api_key=api_key,
            max_tokens=1500,
        )
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)

        self.nlu = TourismNLUTool()
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()

        logger.info("Tourism Multi-Agent System initialized successfully")

    def _execute_pipeline(self, user_input: str) -> dict[str, str]:
        """Execute the tourism tool pipeline.

        Pipeline: NLU(user_input) -> Accessibility(nlu) -> Route(accessibility) + TourismInfo(nlu)
        """
        logger.info("Executing tourism pipeline", input=user_input)

        nlu_result = self.nlu._run(user_input)
        logger.info("NLU analysis completed", result=nlu_result[:200])

        accessibility_result = self.accessibility._run(nlu_result)
        logger.info("Accessibility analysis completed")

        route_result = self.route._run(accessibility_result)
        logger.info("Route planning completed")

        tourism_result = self.tourism_info._run(nlu_result)
        logger.info("Tourism info retrieved")

        return {
            "nlu": nlu_result,
            "accessibility": accessibility_result,
            "route": route_result,
            "tourism_info": tourism_result,
        }

    def _build_response_prompt(self, user_input: str, tool_results: dict[str, str]) -> str:
        """Build the tourism-specific response prompt."""
        return build_response_prompt(user_input=user_input, tool_results=tool_results)
