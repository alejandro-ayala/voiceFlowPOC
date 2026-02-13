"""Excepciones personalizadas del sistema"""

from shared.exceptions.exceptions import (
    EXCEPTION_STATUS_CODES,
    AudioProcessingError,
    AudioProcessingException,
    AuthenticationException,
    BackendCommunicationException,
    ConfigurationException,
    ValidationError,
    ValidationException,
    VoiceFlowException,
)

__all__ = [
    "VoiceFlowException",
    "AudioProcessingException",
    "BackendCommunicationException",
    "ValidationException",
    "ConfigurationException",
    "AuthenticationException",
    "AudioProcessingError",
    "ValidationError",
    "EXCEPTION_STATUS_CODES",
]
