"""
Centralized configuration for VoiceFlow PoC Web UI
Supports local and Azure deployment with environment-based configuration.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment-based configuration.
    Follows SOLID principles for easy deployment configuration changes.
    """
    
    # Application settings
    app_name: str = Field(default="VoiceFlow Tourism PoC", description="Application name")
    app_description: str = Field(default="Accessible Tourism Multi-Agent Assistant", description="Application description")
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
    use_real_agents: bool = Field(default=True, description="Use real LangChain agents (True) or simulation (False)")
    
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
        extra="ignore"
    )


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
            "allow_credentials": True
        }
    else:
        # Development CORS can be more permissive
        return {
            "allow_origins": ["*"],
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "allow_credentials": False
        }
