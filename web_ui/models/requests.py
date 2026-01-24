"""
Pydantic request models for API endpoints.
Provides automatic validation and documentation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class AudioUploadRequest(BaseModel):
    """Request model for audio upload"""
    
    audio_data: str = Field(..., description="Base64 encoded audio data")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(default="audio/wav", description="MIME type of audio file")
    
    @validator("filename")
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        return v.strip()
    
    @validator("audio_data")
    def validate_audio_data(cls, v):
        if not v or len(v) < 100:  # Basic check for minimum data
            raise ValueError("Invalid audio data")
        return v


class AudioTranscriptionRequest(BaseModel):
    """Request model for audio transcription"""
    
    audio_data: str = Field(..., description="Base64 encoded audio data")
    language: str = Field(default="es-ES", description="Language code for transcription")
    format: str = Field(default="wav", description="Audio format")
    
    @validator("audio_data")
    def validate_audio_data(cls, v):
        if not v or len(v) < 100:  # Basic check for minimum data
            raise ValueError("Invalid audio data")
        return v


class ChatMessageRequest(BaseModel):
    """Request model for chat messages"""
    
    message: str = Field(..., description="User message or transcription")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for chat tracking")
    session_id: Optional[str] = Field(default=None, description="Legacy field - use conversation_id instead")
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context data")
    
    @validator("message")
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v.strip()) > 1000:
            raise ValueError("Message too long (max 1000 characters)")
        return v.strip()


class SystemStatusRequest(BaseModel):
    """Request model for system status check"""
    
    check_backend: bool = Field(default=True, description="Include backend system check")
    check_services: bool = Field(default=True, description="Include services health check")


class ConversationRequest(BaseModel):
    """Request model for conversation operations"""
    
    session_id: Optional[str] = Field(default=None, description="Session ID")
    action: str = Field(..., description="Action: 'get', 'clear', 'export'")
    
    @validator("action")
    def validate_action(cls, v):
        allowed_actions = ["get", "clear", "export"]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v


class ChatHistoryRequest(BaseModel):
    """Request model for chat history operations"""
    
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID to retrieve")
    limit: int = Field(default=50, description="Maximum number of messages to retrieve")
    offset: int = Field(default=0, description="Offset for pagination")
    
    @validator("limit")
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        return v
