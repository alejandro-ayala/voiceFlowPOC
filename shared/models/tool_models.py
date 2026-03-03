"""Typed contracts for inter-tool communication in the pipeline."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from shared.models.nlu_models import NLUResult, ResolvedEntities


class AccessibilityInfo(BaseModel):
    """Output of the accessibility analysis tool."""

    accessibility_level: str = "general"
    venue_rating: Optional[float] = None
    facilities: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    accessibility_score: float = 0.0
    certification: Optional[str] = None
    source: str = "unknown"


class RouteOption(BaseModel):
    """A single route option from the route planning tool."""

    transport_type: str
    duration_minutes: Optional[int] = None
    accessibility_score: Optional[float] = None
    description: Optional[str] = None
    alternatives: list[str] = Field(default_factory=list)
    estimated_cost: Optional[str] = None
    source: str = "unknown"


class VenueDetail(BaseModel):
    """Detailed venue information from the tourism info tool."""

    name: str
    venue_type: Optional[str] = None
    opening_hours: Optional[dict[str, Any]] = None
    pricing: Optional[dict[str, Any]] = None
    accessibility_reviews: Optional[dict[str, Any]] = None
    accessibility_services: list[str] = Field(default_factory=list)
    contact: Optional[dict[str, Any]] = None
    source: str = "unknown"


class PlaceCandidate(BaseModel):
    """A resolved place/venue for the pipeline to operate on."""

    name: str
    place_type: Optional[str] = None
    destination: Optional[str] = None
    source: str = "nlu"


class ToolError(BaseModel):
    """A partial error recorded during pipeline execution."""

    source: str
    message: str


class ToolPipelineContext(BaseModel):
    """Accumulator passed through the tool pipeline, gathering results at each stage."""

    user_input: str
    language: str = "es"
    profile_context: Optional[dict[str, Any]] = None

    # Stage 1: NLU + NER
    nlu_result: Optional[NLUResult] = None
    resolved_entities: Optional[ResolvedEntities] = None
    place: Optional[PlaceCandidate] = None

    # Stage 2: Accessibility
    accessibility: Optional[AccessibilityInfo] = None

    # Stage 3: Routes + Venue info
    routes: list[RouteOption] = Field(default_factory=list)
    venue_detail: Optional[VenueDetail] = None

    # Backward compat: raw JSON strings for prompt builder and metadata
    raw_tool_results: dict[str, str] = Field(default_factory=dict)

    # Partial errors
    errors: list[ToolError] = Field(default_factory=list)
