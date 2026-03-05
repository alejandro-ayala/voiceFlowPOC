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


class ExternalAPIException(VoiceFlowException):
    """Exception raised when an external API call fails."""

    pass


class CircuitBreakerOpenException(ExternalAPIException):
    """Exception raised when circuit breaker is open for a service."""

    pass


class RateLimitExceededException(ExternalAPIException):
    """Exception raised when API rate limit is exceeded."""

    pass


class BudgetExceededException(ExternalAPIException):
    """Exception raised when API budget is exceeded."""

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
    ExternalAPIException: 502,
    CircuitBreakerOpenException: 503,
    RateLimitExceededException: 429,
    BudgetExceededException: 503,
    VoiceFlowException: 500,
}
