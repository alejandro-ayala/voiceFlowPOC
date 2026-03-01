"""
Dependency injection setup for FastAPI.
Implements SOLID DIP principle for loose coupling.
"""

from fastapi import Depends

from application.orchestration.backend_adapter import LocalBackendAdapter
from application.services.audio_service import AudioService
from application.services.conversation_service import ConversationService
from integration.configuration.settings import Settings, get_settings
from integration.external_apis.ner_factory import NERServiceFactory
from integration.external_apis.nlu_factory import NLUServiceFactory
from shared.interfaces.interfaces import (
    AudioProcessorInterface,
    BackendInterface,
    ConversationInterface,
)
from shared.interfaces.ner_interface import NERServiceInterface
from shared.interfaces.nlu_interface import NLUServiceInterface


def get_audio_processor(
    settings: Settings = Depends(get_settings),
) -> AudioProcessorInterface:
    """
    Dependency injection for audio processor.
    Returns appropriate implementation based on configuration.
    """
    return AudioService(settings)


def get_backend_adapter(settings: Settings = Depends(get_settings)) -> BackendInterface:
    """
    Dependency injection for backend adapter.
    Can be easily switched to cloud implementation.
    """
    ner_service = get_ner_service(settings)
    nlu_service = get_nlu_service(settings)
    return LocalBackendAdapter(settings, ner_service=ner_service, nlu_service=nlu_service)


def get_ner_service(settings: Settings = Depends(get_settings)) -> NERServiceInterface:
    """
    Dependency injection for NER provider resolved through registry/factory.
    """
    return NERServiceFactory.create_from_settings(settings)


def get_nlu_service(settings: Settings = Depends(get_settings)) -> NLUServiceInterface | None:
    """Dependency injection for NLU provider resolved through registry/factory.

    In shadow mode, returns the primary provider (configured via nlu_provider).
    The backend adapter separately initializes the shadow provider for async comparison.
    """
    if not settings.nlu_enabled:
        return None

    return NLUServiceFactory.create_from_settings(settings)


def get_conversation_service(
    settings: Settings = Depends(get_settings),
) -> ConversationInterface:
    """
    Dependency injection for conversation service.
    Can be easily switched to database-backed implementation.
    """
    return ConversationService(settings)


# Service initialization
async def initialize_services():
    """
    Initialize all services during application startup.
    This function is called once during application lifespan.
    """
    global _backend_service, _audio_service, _conversation_service, _auth_service, _storage_service

    try:
        # Initialize backend service (demo mode)
        settings = get_settings()
        _backend_service = LocalBackendAdapter(settings)

        # Initialize audio service
        _audio_service = AudioService(settings)

        # Initialize conversation service
        _conversation_service = ConversationService(settings)

        # Initialize auth service (stub for future)
        _auth_service = None

        # Initialize storage service (stub for future)
        _storage_service = None

        print("All services initialized successfully")

    except Exception as e:
        print(f"Failed to initialize services: {e}")
        raise


# Cleanup function
async def cleanup_services():
    """
    Clean up services during application shutdown.
    """
    global _backend_service, _audio_service, _conversation_service

    try:
        if _backend_service:
            pass

        if _audio_service:
            pass

        if _conversation_service:
            pass

        print("Services cleaned up successfully")

    except Exception as e:
        print(f"Failed to cleanup services: {e}")


class SimulatedAudioService:
    """Simulated audio service for demo when Azure isn't available"""

    async def transcribe_audio(self, audio_data: bytes, format: str, language: str = "es-ES"):
        """Simulate audio transcription"""
        import asyncio

        await asyncio.sleep(1)

        return type(
            "Result",
            (),
            {
                "transcription": "Esta es una transcripcion simulada del audio",
                "confidence": 0.85,
                "language": language,
                "duration": 3.5,
                "processing_time": 1.2,
            },
        )()

    async def validate_audio(self, audio_data: bytes, format: str):
        """Simulate audio validation"""
        return {
            "valid": True,
            "format": format,
            "duration": len(audio_data) / 16000,
            "file_size": len(audio_data),
            "sample_rate": 16000,
            "channels": 1,
        }
