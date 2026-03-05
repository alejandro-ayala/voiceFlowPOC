"""
Health check endpoints for system monitoring.
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from application.models.responses import StatusEnum, SystemStatusResponse
from integration.configuration.settings import Settings, get_settings
from shared.interfaces.interfaces import AudioProcessorInterface, BackendInterface
from shared.utils.dependencies import get_audio_processor, get_backend_adapter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=SystemStatusResponse)
async def health_check(
    backend: BackendInterface = Depends(get_backend_adapter),
    audio: AudioProcessorInterface = Depends(get_audio_processor),
    settings: Settings = Depends(get_settings),
):
    """
    Basic health check endpoint.
    Returns overall system status and component health.
    """
    try:
        # Check backend status
        backend_status = await backend.get_system_status()

        # Check audio service
        audio_info = await audio.get_service_info()

        # Determine overall health
        system_healthy = backend_status.get("status") in [
            "healthy",
            "operational",
        ] and audio_info.get("is_available", False)

        components = {
            "backend_adapter": {
                "status": backend_status.get("status", "unknown"),
                "description": f"Backend type: {backend_status.get('backend_type', 'unknown')}",
                "details": backend_status,
            },
            "audio_service": {
                "status": ("healthy" if audio_info.get("is_available", False) else "unhealthy"),
                "description": f"STT Backend: {audio_info.get('stt_backend', 'unknown')}",
                "details": audio_info,
            },
            "api_server": {
                "status": "healthy",
                "description": "FastAPI server running",
                "version": settings.version,
            },
        }

        return SystemStatusResponse(
            status=StatusEnum.SUCCESS if system_healthy else StatusEnum.WARNING,
            message=("System operational" if system_healthy else "System partially operational"),
            system_health="healthy" if system_healthy else "partial",
            components=components,
            uptime="running",
            version=settings.version,
        )

    except Exception as e:
        return SystemStatusResponse(
            status=StatusEnum.ERROR,
            message=f"Health check failed: {str(e)}",
            system_health="unhealthy",
            components={"error": {"status": "error", "description": str(e)}},
            version=settings.version,
        )


@router.get("/backend", response_model=dict)
async def backend_health(backend: BackendInterface = Depends(get_backend_adapter)):
    """
    Detailed backend health check.
    """
    try:
        status = await backend.get_system_status()
        return {
            "status": "success",
            "backend_status": status,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/audio", response_model=dict)
async def audio_health():
    """
    Detailed audio service health check.
    """
    try:
        # Test if real Azure STT is available
        has_real_stt = False
        stt_status = "simulation_mode"

        try:
            from integration.external_apis.stt_agent import create_stt_agent

            stt_agent = create_stt_agent()
            if stt_agent is not None:
                has_real_stt = True
                stt_status = "azure_stt_available"
        except Exception:
            pass

        return {
            "status": "success",
            "healthy": True,
            "service_info": {
                "stt_service": stt_status,
                "real_transcription_available": has_real_stt,
                "azure_stt_configured": has_real_stt,
                "fallback_mode": not has_real_stt,
            },
            "supported_formats": ["wav", "mp3", "m4a", "webm", "ogg"],
            "max_file_size": "10MB",
            "max_duration": "30 seconds",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
