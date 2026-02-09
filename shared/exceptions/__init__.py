"""Excepciones personalizadas del sistema"""

from shared.exceptions.exceptions import (
    VoiceFlowException,
    AudioProcessingException,
    BackendCommunicationException,
    ValidationException,
    ConfigurationException,
    AuthenticationException,
    AudioProcessingError,
    ValidationError,
    EXCEPTION_STATUS_CODES,
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
