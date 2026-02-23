"""Canonical NLU models shared between integration and business layers."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class NLUAlternative(BaseModel):
    """Alternative intent classification with confidence."""

    intent: str
    confidence: float = Field(ge=0.0, le=1.0)


class NLUEntitySet(BaseModel):
    """Business entities extracted by NLU providers."""

    destination: Optional[str] = None
    accessibility: Optional[str] = None
    timeframe: Optional[str] = None
    transport_preference: Optional[str] = None
    budget: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class NLUResult(BaseModel):
    """Canonical output of any NLU provider."""

    status: Literal["ok", "fallback", "error"] = "ok"
    intent: str = "general_query"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: NLUEntitySet = Field(default_factory=NLUEntitySet)
    alternatives: list[NLUAlternative] = Field(default_factory=list)
    provider: str = "unknown"
    model: str = "unknown"
    language: str = "es"
    analysis_version: str = "nlu_v3.0"
    latency_ms: int = 0


class ResolvedEntities(BaseModel):
    """Output of entity resolution after merging NLU and NER entities."""

    destination: Optional[str] = None
    locations: list[str] = Field(default_factory=list)
    top_location: Optional[str] = None
    accessibility: Optional[str] = None
    timeframe: Optional[str] = None
    transport_preference: Optional[str] = None
    budget: Optional[str] = None
    resolution_source: dict[str, str] = Field(default_factory=dict)
    conflicts: list[str] = Field(default_factory=list)
