"""
Pydantic response models for API endpoints.
Ensures consistent response structure and automatic documentation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


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


class ChatResponse(BaseResponse):
    """Response model for chat interactions"""
    
    ai_response: Optional[str] = Field(default=None, description="AI assistant response")
    session_id: str = Field(..., description="Session identifier")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    
    # Structured tourism data
    tourism_data: Optional[Dict[str, Any]] = Field(default=None, description="Structured tourism information")
    intent: Optional[str] = Field(default=None, description="Detected user intent")
    entities: Optional[Dict[str, Any]] = Field(default=None, description="Extracted entities")


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
