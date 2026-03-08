"""
Centralized configuration for VoiceFlow PoC Web UI
Supports local and Azure deployment with environment-based configuration.
"""

import json
import os
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment-based configuration.
    Follows SOLID principles for easy deployment configuration changes.
    """

    # Application settings
    app_name: str = Field(default="VoiceFlow Tourism PoC", description="Application name")
    app_description: str = Field(
        default="Accessible Tourism Multi-Agent Assistant",
        description="Application description",
    )
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=True, description="Debug mode")

    # Server settings
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload on changes")

    # CORS settings (for Azure deployment)
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: list[str] = Field(default=["*"], description="CORS allowed methods")
    cors_headers: list[str] = Field(default=["*"], description="CORS allowed headers")

    # Backend integration settings
    backend_timeout: int = Field(default=30, description="Backend request timeout in seconds")
    max_audio_duration: int = Field(default=30, description="Maximum audio recording duration in seconds")
    max_audio_size_mb: int = Field(default=10, description="Maximum audio file size in MB")
    use_real_agents: bool = Field(
        default=True,
        description="Use real LangChain agents (True) or simulation (False)",
    )

    # Audio processing settings
    azure_speech_key: Optional[str] = Field(default=None, description="Azure Speech Services API key")
    azure_speech_region: Optional[str] = Field(default=None, description="Azure Speech Services region")
    stt_service: str = Field(default="azure", description="Speech-to-text service provider")
    supported_formats: str = Field(default="wav,mp3,m4a,flac,ogg", description="Supported audio formats")
    default_sample_rate: int = Field(default=16000, description="Default audio sample rate")
    default_channels: int = Field(default=1, description="Default audio channels")
    whisper_model: str = Field(default="base", description="Whisper model to use for STT")

    # OpenAI settings (for backend service)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")

    # NER settings
    ner_enabled: bool = Field(default=True, description="Enable NER extraction")
    ner_provider: str = Field(default="spacy", description="NER provider")
    ner_default_language: str = Field(default="es", description="Default NER language")
    ner_model_map: str = Field(
        default='{"es":"es_core_news_md","en":"en_core_web_sm"}',
        description="JSON mapping language->model for NER providers",
    )
    ner_fallback_model: str = Field(default="es_core_news_sm", description="Fallback NER model")
    ner_confidence_threshold: float = Field(default=0.6, description="Minimum NER confidence threshold")

    # NLU settings
    nlu_enabled: bool = Field(default=True, description="Enable NLU service")
    nlu_provider: str = Field(default="openai", description="NLU provider: openai, keyword, or custom")
    nlu_default_language: str = Field(default="es", description="Default NLU language")
    nlu_openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model for NLU classification")
    nlu_confidence_threshold: float = Field(default=0.40, description="Min confidence for non-fallback")
    nlu_fallback_intent: str = Field(default="general_query", description="Intent when below threshold")
    nlu_shadow_mode: bool = Field(
        default=False,
        description="Enable shadow comparison: run primary + shadow provider in parallel,"
        " logging results without affecting response",
    )
    nlu_shadow_provider: str = Field(
        default="keyword",
        description="Shadow comparison provider (used only when nlu_shadow_mode=true)."
        " Can be different from nlu_provider",
    )

    # LLM synthesis settings
    llm_model: str = Field(default="gpt-4", description="LLM model for response synthesis")
    llm_temperature: float = Field(default=0.3, description="LLM temperature for synthesis")
    llm_max_tokens: int = Field(default=2500, description="LLM max tokens for synthesis")

    # External API settings (Phase 1)
    google_api_key: Optional[str] = Field(default=None, description="Google API key for Places + Routes APIs")
    google_places_cache_ttl: int = Field(default=86400, description="Google Places cache TTL in seconds (24h)")
    openroute_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouteService API key (optional, for higher limits)",
    )
    tool_timeout_seconds: float = Field(default=3.0, description="External API tool call timeout in seconds")

    # Resilience settings
    circuit_breaker_threshold: int = Field(default=5, description="Consecutive failures before circuit opens")
    circuit_breaker_recovery_seconds: int = Field(default=60, description="Seconds before circuit breaker half-opens")
    api_rate_limit_rps: int = Field(default=10, description="API calls per second limit")
    api_budget_per_hour: float = Field(default=1.0, description="Max estimated API cost per hour in USD")

    # Provider selection (local = fallback to mock data)
    places_provider: str = Field(default="local", description="Places provider: google, local")
    directions_provider: str = Field(
        default="local",
        description="Directions provider: google, openroute, local",
    )
    accessibility_provider: str = Field(
        default="local",
        description="Accessibility provider: google, overpass, local",
    )
    accessibility_debug_raw: bool = Field(
        default=False,
        description="Expose full raw Overpass payload in tool outputs for temporary debugging",
    )

    # Azure deployment settings (future)
    azure_webapp_name: Optional[str] = Field(default=None, description="Azure Web App name")
    azure_resource_group: Optional[str] = Field(default=None, description="Azure Resource Group")
    azure_storage_account: Optional[str] = Field(default=None, description="Azure Storage Account")

    # Authentication settings (future)
    auth_enabled: bool = Field(default=False, description="Enable authentication")
    auth_provider: Optional[str] = Field(default=None, description="Authentication provider")

    # Database settings (future)
    database_enabled: bool = Field(default=False, description="Enable database")
    database_url: Optional[str] = Field(default=None, description="Database connection URL")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(levelname)s - %(message)s", description="Log format")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="VOICEFLOW_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def resolve_openai_api_key(self) -> "Settings":
        """Resolve OpenAI key from a single canonical env var when not explicitly set.

        Source of truth (preferred): OPENAI_API_KEY
        Backward compatibility: VOICEFLOW_OPENAI_API_KEY

        Explicit constructor values (including None) are respected.
        """
        if self.openai_api_key:
            return self

        if "openai_api_key" in self.model_fields_set:
            return self

        canonical_key = os.getenv("OPENAI_API_KEY")
        legacy_key = os.getenv("VOICEFLOW_OPENAI_API_KEY")
        self.openai_api_key = canonical_key or legacy_key
        return self


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency injection function for FastAPI.
    Allows easy testing and configuration override.
    """
    return settings


def is_production() -> bool:
    """Check if running in production environment"""
    return not settings.debug


def is_azure_deployment() -> bool:
    """Check if running on Azure deployment"""
    return settings.azure_webapp_name is not None


def get_cors_config() -> dict:
    """Get CORS configuration based on environment"""
    if is_production():
        # Production CORS should be more restrictive
        return {
            "allow_origins": settings.cors_origins,
            "allow_methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Authorization", "Content-Type"],
            "allow_credentials": True,
        }
    else:
        # Development CORS can be more permissive
        return {
            "allow_origins": ["*"],
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "allow_credentials": False,
        }


def get_ner_model_map(raw_value: Optional[str] = None) -> dict[str, str]:
    """Parse NER model mapping from settings with safe fallback defaults."""
    default_map = {
        "es": "es_core_news_md",
        "en": "en_core_web_sm",
    }

    source_value = raw_value if raw_value is not None else settings.ner_model_map

    try:
        parsed = json.loads(source_value)
        if not isinstance(parsed, dict):
            return default_map

        normalized_map: dict[str, str] = {}
        for key, value in parsed.items():
            if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                normalized_map[key.strip().lower()] = value.strip()

        return normalized_map or default_map
    except (TypeError, ValueError, json.JSONDecodeError):
        return default_map
