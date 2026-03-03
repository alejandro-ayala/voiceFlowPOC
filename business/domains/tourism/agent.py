"""Tourism domain orchestrator - wires core framework with tourism-specific tools and prompts."""

import asyncio
import json
import re
import time
from typing import Optional

import structlog
from langchain_openai import ChatOpenAI

from business.core.canonicalizer import canonicalize_tourism_data
from business.core.orchestrator import MultiAgentOrchestrator
from business.domains.tourism.entity_resolver import EntityResolver
from business.domains.tourism.prompts.response_prompt import build_response_prompt
from business.domains.tourism.prompts.system_prompt import SYSTEM_PROMPT
from business.domains.tourism.tools.accessibility_tool import AccessibilityAnalysisTool
from business.domains.tourism.tools.location_ner_tool import LocationNERTool
from business.domains.tourism.tools.nlu_tool import TourismNLUTool
from business.domains.tourism.tools.route_planning_tool import RoutePlanningTool
from business.domains.tourism.tools.tourism_info_tool import TourismInfoTool
from integration.configuration.settings import Settings
from shared.interfaces.ner_interface import NERServiceInterface
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUResult
from shared.models.tool_models import PlaceCandidate, ToolPipelineContext

logger = structlog.get_logger(__name__)


class TourismMultiAgent(MultiAgentOrchestrator):
    """
    Orchestrator for the accessible tourism domain (Madrid).

    Coordinates 4 specialized tools through a fixed pipeline:
    NLU -> Accessibility -> Route Planning + Tourism Info -> LLM synthesis.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        ner_service: Optional[NERServiceInterface] = None,
        nlu_service: Optional[NLUServiceInterface] = None,
    ):
        """Initialize the tourism multi-agent system."""
        logger.info("Initializing Tourism Multi-Agent System")

        _settings = Settings()
        api_key = openai_api_key or _settings.openai_api_key
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable."
            )

        llm = ChatOpenAI(
            model=_settings.llm_model,
            temperature=_settings.llm_temperature,
            openai_api_key=api_key,
            max_tokens=_settings.llm_max_tokens,
        )
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)

        self.nlu = TourismNLUTool(nlu_service=nlu_service)
        self.location_ner = LocationNERTool(ner_service=ner_service)
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()
        self.entity_resolver = EntityResolver()

        logger.info("Tourism Multi-Agent System initialized successfully")

    # ------------------------------------------------------------------ #
    #  Shared helpers for pipeline instrumentation                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_and_summarize(raw: str) -> tuple[object, str]:
        """Parse JSON from raw tool output and build a summary string."""
        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None

        summary = None
        if isinstance(parsed, dict):
            summary = (
                parsed.get("intent")
                or parsed.get("accessibility_level")
                or parsed.get("venue")
            )
            if summary is None:
                keys = list(parsed.keys())[:3]
                summary = ",".join(keys)
        else:
            summary = (raw or "").strip()[:120]

        return parsed, summary

    @staticmethod
    def _log_ner_observability(parsed: object, duration_ms: int) -> None:
        """Emit observability log for LocationNER tool."""
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

    def _record_tool(
        self,
        name: str,
        tool_name: str,
        raw: str,
        duration_ms: int,
        pipeline_steps: list[dict],
        tool_results: dict[str, str],
        parsed_tools: dict[str, object],
    ) -> object:
        """Record a tool result into pipeline tracking structures."""
        parsed, summary = self._parse_and_summarize(raw)

        pipeline_steps.append(
            {
                "name": name,
                "tool": tool_name,
                "status": "completed",
                "duration_ms": duration_ms,
                "summary": summary,
            }
        )

        tool_results[name.lower()] = raw
        parsed_tools[name.lower()] = parsed

        if name == "LocationNER":
            self._log_ner_observability(parsed, duration_ms)

        logger.info(f"{name} completed", duration_ms=duration_ms)
        return parsed

    def _run_tool_sync(
        self,
        name: str,
        tool,
        input_data: str,
        pipeline_steps: list[dict],
        tool_results: dict[str, str],
        parsed_tools: dict[str, object],
    ) -> tuple[str, object]:
        """Execute a tool synchronously with timing instrumentation."""
        start = time.perf_counter()
        raw = tool._run(input_data)
        duration_ms = int((time.perf_counter() - start) * 1000)

        parsed = self._record_tool(
            name,
            getattr(tool, "name", name.lower()),
            raw,
            duration_ms,
            pipeline_steps,
            tool_results,
            parsed_tools,
        )
        return raw, parsed

    async def _run_tool_async(
        self,
        name: str,
        tool,
        input_data: str,
        pipeline_steps: list[dict],
        tool_results: dict[str, str],
        parsed_tools: dict[str, object],
    ) -> tuple[str, object]:
        """Execute a tool asynchronously with timing instrumentation."""
        start = time.perf_counter()
        raw = await tool._arun(input_data)
        duration_ms = int((time.perf_counter() - start) * 1000)

        parsed = self._record_tool(
            name,
            getattr(tool, "name", name.lower()),
            raw,
            duration_ms,
            pipeline_steps,
            tool_results,
            parsed_tools,
        )
        return raw, parsed

    # ------------------------------------------------------------------ #
    #  NLU + NER result parsing (shared between sync and async pipelines) #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_nlu_result(nlu_parsed: object) -> Optional[NLUResult]:
        """Parse NLU dict into a validated NLUResult model."""
        if not isinstance(nlu_parsed, dict):
            return None
        try:
            return NLUResult.model_validate(
                {
                    "status": nlu_parsed.get("status", "ok"),
                    "intent": nlu_parsed.get("intent", "general_query"),
                    "confidence": nlu_parsed.get("confidence", 0.0),
                    "entities": nlu_parsed.get("entities", {}),
                    "alternatives": nlu_parsed.get("alternatives", []),
                    "provider": nlu_parsed.get("provider", "unknown"),
                    "model": nlu_parsed.get("model", "unknown"),
                    "language": nlu_parsed.get("entities", {}).get("language", "es"),
                    "analysis_version": nlu_parsed.get(
                        "analysis_version", "nlu_v3.0"
                    ),
                    "latency_ms": nlu_parsed.get("latency_ms", 0),
                }
            )
        except Exception:
            return None

    @staticmethod
    def _parse_ner_locations(
        location_ner_parsed: object,
    ) -> tuple[list[str], Optional[str]]:
        """Extract location list and top_location from NER parsed output."""
        ner_locations: list[str] = []
        ner_top_location: str | None = None
        if isinstance(location_ner_parsed, dict):
            locations_raw = location_ner_parsed.get("locations", [])
            if isinstance(locations_raw, list):
                for item in locations_raw:
                    if isinstance(item, str):
                        ner_locations.append(item)
                    elif isinstance(item, dict) and isinstance(item.get("name"), str):
                        ner_locations.append(item["name"])
            top_location_value = location_ner_parsed.get("top_location")
            ner_top_location = (
                top_location_value if isinstance(top_location_value, str) else None
            )
        return ner_locations, ner_top_location

    def _build_metadata(
        self,
        pipeline_steps: list[dict],
        parsed_tools: dict[str, object],
        resolved_entities,
    ) -> dict:
        """Build the metadata dict from parsed tool outputs."""
        # Build tourism_data from parsed tools
        tourism_data = None
        try:
            tourism_info = (
                parsed_tools.get("venue info")
                or parsed_tools.get("tourism_info")
                or parsed_tools.get("venue")
            )
            routes = parsed_tools.get("routes") or parsed_tools.get("route")
            accessibility = parsed_tools.get("accessibility")

            if (
                isinstance(tourism_info, dict)
                or isinstance(routes, dict)
                or isinstance(accessibility, dict)
            ):
                routes_val = None
                if isinstance(routes, dict) and routes.get("routes"):
                    routes_val = routes.get("routes")
                elif isinstance(routes, list):
                    routes_val = routes
                tourism_data = {
                    "venue": (tourism_info if isinstance(tourism_info, dict) else None),
                    "routes": routes_val,
                    "accessibility": (
                        accessibility if isinstance(accessibility, dict) else None
                    ),
                }
        except Exception:
            tourism_data = None

        try:
            tourism_data = (
                canonicalize_tourism_data(tourism_data) if tourism_data else None
            )
        except Exception:
            tourism_data = None

        intent = None
        entities = None
        nlu_parsed = parsed_tools.get("nlu")
        if isinstance(nlu_parsed, dict):
            intent = nlu_parsed.get("intent")
            if resolved_entities is not None:
                entities = resolved_entities.model_dump()
            else:
                entities = nlu_parsed.get("entities")

        return {
            "pipeline_steps": pipeline_steps,
            "tourism_data": tourism_data,
            "intent": intent,
            "entities": entities,
            "tool_results_parsed": parsed_tools,
        }

    # ------------------------------------------------------------------ #
    #  Async-native pipeline (primary path)                               #
    # ------------------------------------------------------------------ #

    async def _execute_pipeline_async(
        self, user_input: str, profile_context: Optional[dict] = None
    ) -> tuple[dict[str, str], dict]:
        """Execute the tourism tool pipeline asynchronously (native async).

        Eliminates nested asyncio.run() by using await directly.
        Uses ToolPipelineContext for typed inter-tool communication.
        """
        self._current_profile_context = profile_context

        logger.info("Executing tourism pipeline (async)", input=user_input)

        pipeline_steps: list[dict] = []
        tool_results: dict[str, str] = {}
        parsed_tools: dict[str, object] = {}

        # -- Step 1: NLU + NER in parallel (native async, no asyncio.run) --
        parallel_start = time.perf_counter()
        nlu_raw, location_ner_raw = await asyncio.gather(
            self.nlu._arun(user_input),
            self.location_ner._arun(user_input),
        )
        parallel_duration_ms = int((time.perf_counter() - parallel_start) * 1000)

        nlu_parsed = self._record_tool(
            "NLU", self.nlu.name, nlu_raw, parallel_duration_ms,
            pipeline_steps, tool_results, parsed_tools,
        )
        location_ner_parsed = self._record_tool(
            "LocationNER", self.location_ner.name, location_ner_raw,
            parallel_duration_ms, pipeline_steps, tool_results, parsed_tools,
        )

        # -- Parse NLU + NER and resolve entities --
        nlu_result = self._parse_nlu_result(nlu_parsed)
        ner_locations, ner_top_location = self._parse_ner_locations(location_ner_parsed)

        resolved_entities = None
        if nlu_result is not None:
            resolved_entities = self.entity_resolver.resolve(
                nlu_result, ner_locations, ner_top_location
            )

        # -- Build typed pipeline context --
        ctx = ToolPipelineContext(
            user_input=user_input,
            profile_context=profile_context,
            nlu_result=nlu_result,
            resolved_entities=resolved_entities,
            place=PlaceCandidate(
                name=(resolved_entities.destination if resolved_entities and resolved_entities.destination else "general"),
                destination=(resolved_entities.destination if resolved_entities else None),
            ),
            raw_tool_results=dict(tool_results),
        )

        # -- Step 2: Domain tools with typed context --
        acc_start = time.perf_counter()
        ctx = await self.accessibility.execute(ctx)
        acc_duration = int((time.perf_counter() - acc_start) * 1000)
        # Record in pipeline tracking
        if "accessibility" in ctx.raw_tool_results:
            acc_parsed, acc_summary = self._parse_and_summarize(
                ctx.raw_tool_results["accessibility"]
            )
            pipeline_steps.append({
                "name": "Accessibility",
                "tool": self.accessibility.name,
                "status": "completed",
                "duration_ms": acc_duration,
                "summary": acc_summary,
            })
            tool_results["accessibility"] = ctx.raw_tool_results["accessibility"]
            parsed_tools["accessibility"] = acc_parsed

        route_start = time.perf_counter()
        ctx = await self.route.execute(ctx)
        route_duration = int((time.perf_counter() - route_start) * 1000)
        if "routes" in ctx.raw_tool_results:
            route_parsed, route_summary = self._parse_and_summarize(
                ctx.raw_tool_results["routes"]
            )
            pipeline_steps.append({
                "name": "Routes",
                "tool": self.route.name,
                "status": "completed",
                "duration_ms": route_duration,
                "summary": route_summary,
            })
            tool_results["routes"] = ctx.raw_tool_results["routes"]
            parsed_tools["routes"] = route_parsed

        venue_start = time.perf_counter()
        ctx = await self.tourism_info.execute(ctx)
        venue_duration = int((time.perf_counter() - venue_start) * 1000)
        if "venue info" in ctx.raw_tool_results:
            venue_parsed, venue_summary = self._parse_and_summarize(
                ctx.raw_tool_results["venue info"]
            )
            pipeline_steps.append({
                "name": "Venue Info",
                "tool": self.tourism_info.name,
                "status": "completed",
                "duration_ms": venue_duration,
                "summary": venue_summary,
            })
            tool_results["venue info"] = ctx.raw_tool_results["venue info"]
            parsed_tools["venue info"] = venue_parsed

        metadata = self._build_metadata(pipeline_steps, parsed_tools, resolved_entities)

        return tool_results, metadata

    # ------------------------------------------------------------------ #
    #  Sync pipeline (legacy wrapper — delegates to async)                #
    # ------------------------------------------------------------------ #

    def _execute_pipeline(
        self, user_input: str, profile_context: Optional[dict] = None
    ) -> tuple[dict[str, str], dict]:
        """Execute the tourism tool pipeline synchronously (legacy).

        Delegates to the async-native pipeline via asyncio.run().
        Safe to call from threads without an active event loop.
        """
        return asyncio.run(
            self._execute_pipeline_async(user_input, profile_context=profile_context)
        )

    # ------------------------------------------------------------------ #
    #  Prompt building and structured data extraction                     #
    # ------------------------------------------------------------------ #

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

    def _extract_structured_data(
        self, llm_text: str, metadata: dict
    ) -> tuple[str, dict]:
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

        existing = metadata.get("tourism_data")
        if not existing:
            metadata["tourism_data"] = llm_tourism_data
            logger.info("Using LLM-generated tourism_data (no tool data available)")
        else:
            existing_venue = existing.get("venue") or {}
            is_default = (
                existing_venue.get("accessibility_score") == 6.0
                or existing_venue.get("name", "").startswith("Gu")
                or not existing_venue.get("name")
            )
            if is_default:
                metadata["tourism_data"] = llm_tourism_data
                logger.info(
                    "Replaced default tool tourism_data with LLM-generated data"
                )
            else:
                logger.info("Keeping tool-derived tourism_data (specific venue data)")

        return clean_text, metadata
