"""Tourism domain orchestrator - wires core framework with tourism-specific tools and prompts."""

import json
import os
import re
from typing import Optional

import structlog
from langchain_openai import ChatOpenAI

from business.core.canonicalizer import canonicalize_tourism_data
from business.core.orchestrator import MultiAgentOrchestrator
from business.domains.tourism.prompts.response_prompt import build_response_prompt
from business.domains.tourism.prompts.system_prompt import SYSTEM_PROMPT
from business.domains.tourism.tools.accessibility_tool import AccessibilityAnalysisTool
from business.domains.tourism.tools.location_ner_tool import LocationNERTool
from business.domains.tourism.tools.nlu_tool import TourismNLUTool
from business.domains.tourism.tools.route_planning_tool import RoutePlanningTool
from business.domains.tourism.tools.tourism_info_tool import TourismInfoTool
from shared.interfaces.ner_interface import NERServiceInterface

logger = structlog.get_logger(__name__)


class TourismMultiAgent(MultiAgentOrchestrator):
    """
    Orchestrator for the accessible tourism domain (Madrid).

    Coordinates 4 specialized tools through a fixed pipeline:
    NLU -> Accessibility -> Route Planning + Tourism Info -> LLM synthesis.
    """

    def __init__(self, openai_api_key: Optional[str] = None, ner_service: Optional[NERServiceInterface] = None):
        """Initialize the tourism multi-agent system."""
        logger.info("Initializing Tourism Multi-Agent System")

        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            openai_api_key=api_key,
            max_tokens=2500,
        )
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)

        self.nlu = TourismNLUTool()
        self.location_ner = LocationNERTool(ner_service=ner_service)
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()

        logger.info("Tourism Multi-Agent System initialized successfully")

    def _execute_pipeline(self, user_input: str, profile_context: Optional[dict] = None) -> tuple[dict[str, str], dict]:
        """Execute the tourism tool pipeline with timing instrumentation.

        Receives profile_context for ranking bias application.
        Returns a tuple: (tool_results: dict[str,str], metadata: dict)
        metadata contains `pipeline_steps`, parsed tool outputs and basic intent/entities.
        """
        # Store profile context for use in tool execution
        self._current_profile_context = profile_context
        import json
        import time

        logger.info("Executing tourism pipeline (instrumented)", input=user_input)

        pipeline_steps: list[dict] = []
        tool_results: dict[str, str] = {}
        parsed_tools: dict[str, object] = {}

        # helper to run a tool and capture timing + parsed output
        def run_tool(name: str, tool, input_data: str):
            start = time.perf_counter()
            raw = tool._run(input_data)
            end = time.perf_counter()
            duration_ms = int((end - start) * 1000)

            # try to parse JSON result
            parsed = None
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = None

            # build summary heuristics
            summary = None
            if isinstance(parsed, dict):
                # prefer concise known keys
                summary = parsed.get("intent") or parsed.get("accessibility_level") or parsed.get("venue")
                if summary is None:
                    # fallback to presence of keys
                    keys = list(parsed.keys())[:3]
                    summary = ",".join(keys)
            else:
                summary = (raw or "").strip()[:120]

            pipeline_steps.append(
                {
                    "name": name,
                    "tool": getattr(tool, "name", name.lower()),
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "summary": summary,
                }
            )

            if name == "LocationNER":
                location_count = 0
                provider = None
                model = None
                parsed_language = None
                parsed_status = None
                if isinstance(parsed, dict):
                    locations = parsed.get("locations")
                    location_count = len(locations) if isinstance(locations, list) else 0
                    provider = parsed.get("provider")
                    model = parsed.get("model")
                    parsed_language = parsed.get("language")
                    parsed_status = parsed.get("status")

                logger.info(
                    "location_ner_observability",
                    provider=provider,
                    model=model,
                    language=parsed_language,
                    latency_ms=duration_ms,
                    location_count=location_count,
                    status=parsed_status,
                )

            tool_results[name.lower()] = raw
            parsed_tools[name.lower()] = parsed
            logger.info(f"{name} completed", duration_ms=duration_ms)

            return raw, parsed

        # NLU
        nlu_raw, nlu_parsed = run_tool("NLU", self.nlu, user_input)

        # Location NER (input: raw user text to avoid losing entities normalized by NLU)
        run_tool("LocationNER", self.location_ner, user_input)

        # Accessibility (input: NLU raw)
        nlu_raw = tool_results.get("nlu") or ""
        run_tool("Accessibility", self.accessibility, nlu_raw)

        # Routes (input: accessibility raw)
        accessibility_raw = tool_results.get("accessibility") or ""
        run_tool("Routes", self.route, accessibility_raw)

        # Tourism info (input: NLU raw)
        run_tool("Venue Info", self.tourism_info, nlu_raw)

        # Build tourism_data from parsed tools where possible
        tourism_data = None
        try:
            tourism_info = (
                parsed_tools.get("venue info") or parsed_tools.get("tourism_info") or parsed_tools.get("venue")
            )
            routes = parsed_tools.get("routes") or parsed_tools.get("route")
            accessibility = parsed_tools.get("accessibility")

            # normalize names
            if isinstance(tourism_info, dict) or isinstance(routes, dict) or isinstance(accessibility, dict):
                routes_val = None
                if isinstance(routes, dict) and routes.get("routes"):
                    routes_val = routes.get("routes")
                elif isinstance(routes, list):
                    routes_val = routes
                tourism_data = {
                    "venue": (tourism_info if isinstance(tourism_info, dict) else None),
                    "routes": routes_val,
                    "accessibility": (accessibility if isinstance(accessibility, dict) else None),
                }
        except Exception:
            tourism_data = None

        # Canonicalize tourism_data into the SSOT used by the API/UI.
        try:
            tourism_data = canonicalize_tourism_data(tourism_data) if tourism_data else None
        except Exception:
            tourism_data = None

        # attempt to extract intent/entities from NLU parsed
        intent = None
        entities = None
        nlu_parsed = parsed_tools.get("nlu")
        if isinstance(nlu_parsed, dict):
            intent = nlu_parsed.get("intent")
            entities = nlu_parsed.get("entities")

        metadata = {
            "pipeline_steps": pipeline_steps,
            "tourism_data": tourism_data,
            "intent": intent,
            "entities": entities,
            "tool_results_parsed": parsed_tools,
        }

        return tool_results, metadata

    def _build_response_prompt(
        self,
        user_input: str,
        tool_results: dict[str, str],
        profile_context: Optional[dict] = None,
    ) -> str:
        """Build the tourism-specific response prompt."""
        return build_response_prompt(
            user_input=user_input,
            tool_results=tool_results,
            profile_context=profile_context,
        )

    def _extract_structured_data(self, llm_text: str, metadata: dict) -> tuple[str, dict]:
        """Extract JSON tourism_data block from LLM response and merge into metadata."""
        match = re.search(r"```json\s*(\{.*?\})\s*```", llm_text, re.DOTALL)
        if not match:
            return llm_text, metadata

        json_block = match.group(1)
        clean_text = llm_text[: match.start()].rstrip()

        try:
            raw_data = json.loads(json_block)
        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON block", error=str(e))
            return clean_text, metadata

        llm_tourism_data = canonicalize_tourism_data(raw_data)
        if not llm_tourism_data:
            logger.warning("LLM tourism_data failed canonicalization")
            return clean_text, metadata

        # Merge: prefer LLM data over tool data (tool data is often generic defaults)
        existing = metadata.get("tourism_data")
        if not existing:
            metadata["tourism_data"] = llm_tourism_data
            logger.info("Using LLM-generated tourism_data (no tool data available)")
        else:
            # If existing tool data looks like a generic default (score 6.0, name contains "Guía"),
            # prefer the LLM-generated data which has contextual information
            existing_venue = existing.get("venue") or {}
            is_default = (
                existing_venue.get("accessibility_score") == 6.0
                or existing_venue.get("name", "").startswith("Gu")
                or not existing_venue.get("name")
            )
            if is_default:
                metadata["tourism_data"] = llm_tourism_data
                logger.info("Replaced default tool tourism_data with LLM-generated data")
            else:
                logger.info("Keeping tool-derived tourism_data (specific venue data)")

        return clean_text, metadata
