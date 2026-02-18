"""
Pydantic response models for API endpoints.
Ensures consistent response structure and automatic documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, root_validator, validator


class PipelineStatus(str):
    """Allowed pipeline step statuses"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class StatusEnum(str, Enum):
    """Status enumeration for responses"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BaseResponse(BaseModel):
    """Base response model with common fields"""

    status: StatusEnum = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    class Config:
        use_enum_values = True


class AudioProcessingResponse(BaseResponse):
    """Response model for audio processing"""

    transcription: Optional[str] = Field(default=None, description="Transcribed text")
    confidence: Optional[float] = Field(default=None, description="Transcription confidence score")
    duration: Optional[float] = Field(default=None, description="Audio duration in seconds")
    language: Optional[str] = Field(default="es-ES", description="Detected language")


class AudioTranscriptionResponse(BaseResponse):
    """Response model for audio transcription specifically"""

    transcription: str = Field(..., description="Transcribed text")
    confidence: Optional[float] = Field(default=None, description="Transcription confidence")
    language: Optional[str] = Field(default="es-ES", description="Detected language")
    is_simulation: bool = Field(default=False, description="Whether this is a simulated response")


class AudioProcessingStatusResponse(BaseResponse):
    """Response model for audio processing status"""

    processing_id: str = Field(..., description="Processing request ID")
    is_complete: bool = Field(..., description="Whether processing is complete")
    progress: Optional[float] = Field(default=None, description="Processing progress (0-1)")
    estimated_completion: Optional[datetime] = Field(default=None, description="Estimated completion time")


class PipelineStep(BaseModel):
    """A single step in the agent pipeline"""

    name: str = Field(..., description="Display name of the step")
    tool: str = Field(..., description="Tool identifier")
    status: str = Field(default=PipelineStatus.PENDING, description="pending|processing|completed|error")
    duration_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    summary: Optional[str] = Field(default=None, description="Brief summary of step output")

    @validator("status")
    def validate_status(cls, v):
        allowed = {PipelineStatus.PENDING, PipelineStatus.PROCESSING, PipelineStatus.COMPLETED, PipelineStatus.ERROR}
        if v not in allowed:
            return PipelineStatus.PENDING
        return v

    @validator("duration_ms", pre=True)
    def coerce_duration(cls, v):
        try:
            if v is None:
                return None
            iv = int(v)
            return iv if iv >= 0 else None
        except Exception:
            return None

    @validator("summary", pre=True, always=True)
    def trim_summary(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s[:240]


class Venue(BaseModel):
    name: str
    type: Optional[str] = None
    accessibility_score: Optional[float] = None
    certification: Optional[str] = None
    facilities: Optional[List[str]] = None
    opening_hours: Optional[Dict[str, str]] = None
    pricing: Optional[Dict[str, str]] = None

    @validator("accessibility_score", pre=True)
    def coerce_score(cls, v):
        if v is None:
            return None
        try:
            fv = float(v)
            if fv < 0:
                fv = 0.0
            if fv > 10:
                fv = 10.0
            return round(fv, 2)
        except Exception:
            return None

    @validator("facilities", pre=True)
    def ensure_facilities_list(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return [str(x) for x in v][:20]
        # if comma-separated string
        return [s.strip() for s in str(v).split(",") if s.strip()][:20]


class Route(BaseModel):
    transport: Optional[str] = None
    line: Optional[str] = None
    duration: Optional[str] = None
    accessibility: Optional[str] = None
    cost: Optional[str] = None
    steps: Optional[List[str]] = None

    @validator("steps", pre=True)
    def ensure_steps(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return [str(s) for s in v][:50]
        return [s.strip() for s in str(v).split("\n") if s.strip()][:50]


class Accessibility(BaseModel):
    level: Optional[str] = None
    score: Optional[float] = None
    certification: Optional[str] = None
    facilities: Optional[List[str]] = None
    services: Optional[Dict[str, str]] = None

    @validator("score", pre=True)
    def coerce_score(cls, v):
        if v is None:
            return None
        try:
            fv = float(v)
            if fv < 0:
                fv = 0.0
            if fv > 10:
                fv = 10.0
            return round(fv, 2)
        except Exception:
            return None

    @validator("facilities", pre=True)
    def ensure_facilities(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return [str(x) for x in v][:20]
        return [s.strip() for s in str(v).split(",") if s.strip()][:20]


class TourismData(BaseModel):
    venue: Optional[Venue] = None
    routes: Optional[List[Route]] = None
    accessibility: Optional[Accessibility] = None

    @root_validator(pre=True)
    def ensure_structure(cls, values):
        # allow routes being a dict with 'routes' key
        routes = values.get("routes")
        if routes and isinstance(routes, dict) and "routes" in routes:
            values["routes"] = routes.get("routes")
        return values


class ChatResponse(BaseResponse):
    """Response model for chat interactions"""

    ai_response: Optional[str] = Field(default=None, description="AI assistant response")
    session_id: str = Field(..., description="Session identifier")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")

    # Structured tourism data
    tourism_data: Optional[TourismData] = Field(default=None, description="Structured tourism information")
    intent: Optional[str] = Field(default=None, description="Detected user intent")
    entities: Optional[Dict[str, Any]] = Field(default=None, description="Extracted entities")

    # Pipeline visualization
    pipeline_steps: Optional[List[PipelineStep]] = Field(
        default=None, description="Per-tool pipeline step timing and status"
    )

    class Config:
        arbitrary_types_allowed = True


class SystemStatusResponse(BaseResponse):
    """Response model for system status"""

    system_health: str = Field(..., description="Overall system health")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Individual component status")
    uptime: Optional[str] = Field(default=None, description="System uptime")
    version: str = Field(..., description="Application version")


class ConversationHistoryResponse(BaseResponse):
    """Response model for conversation history"""

    session_id: str = Field(..., description="Session identifier")
    messages: List[Dict[str, Any]] = Field(..., description="Conversation messages")
    total_messages: int = Field(..., description="Total number of messages")
    session_start: Optional[datetime] = Field(default=None, description="Session start time")


class ConversationResponse(BaseResponse):
    """Response model for individual conversation data"""

    conversation_id: str = Field(..., description="Conversation identifier")
    messages: List[Dict[str, Any]] = Field(..., description="Conversation messages")
    created_at: Optional[str] = Field(default=None, description="Conversation creation time")
    updated_at: Optional[str] = Field(default=None, description="Last update time")
    message_count: int = Field(..., description="Number of messages in conversation")


class ConversationListResponse(BaseResponse):
    """Response model for conversation listing"""

    conversations: List[Dict[str, Any]] = Field(..., description="List of conversations")
    total_count: int = Field(..., description="Total number of conversations")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")


class ErrorResponse(BaseResponse):
    """Response model for errors"""

    error_code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested actions")
