"""
Custom exceptions for the VoiceFlow PoC application.
Provides structured error handling throughout the application.
"""

from typing import Any, Dict, Optional


class VoiceFlowException(Exception):
    """Base exception for VoiceFlow PoC application"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AudioProcessingException(VoiceFlowException):
    """Exception raised during audio processing operations"""

    pass


class BackendCommunicationException(VoiceFlowException):
    """Exception raised during backend communication"""

    pass


class ValidationException(VoiceFlowException):
    """Exception raised during data validation"""

    pass


class ConfigurationException(VoiceFlowException):
    """Exception raised for configuration issues"""

    pass


class AuthenticationException(VoiceFlowException):
    """Exception raised for authentication issues"""

    pass


# Aliases for backward compatibility
AudioProcessingError = AudioProcessingException
ValidationError = ValidationException


# HTTP Exception mappings for FastAPI
EXCEPTION_STATUS_CODES = {
    AudioProcessingException: 422,
    BackendCommunicationException: 503,
    ValidationException: 400,
    ConfigurationException: 500,
    AuthenticationException: 401,
    VoiceFlowException: 500,
}
