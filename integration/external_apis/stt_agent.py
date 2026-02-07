from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
import structlog

from shared.interfaces.stt_interface import STTServiceInterface, STTServiceError, AudioFormatError
from integration.external_apis.stt_factory import STTServiceFactory

logger = structlog.get_logger(__name__)


class VoiceflowSTTAgent:
    """
    Agente principal de Speech-to-Text para el sistema multiagente.

    Implementa el principio de Responsabilidad Única (SRP) - coordina la transcripción
    de audio pero delega la implementación específica a los servicios STT.

    Cumple con el principio de Inversión de Dependencias (DIP) - depende de la abstracción
    STTServiceInterface, no de implementaciones concretas.
    """

    def __init__(self, stt_service: STTServiceInterface, agent_id: str = "stt_agent_001"):
        """
        Inicializa el agente STT.

        Args:
            stt_service: Servicio STT a utilizar
            agent_id: Identificador único del agente
        """
        self.stt_service = stt_service
        self.agent_id = agent_id
        self._transcription_history: list[Dict[str, Any]] = []

        logger.info("VoiceflowSTTAgent inicializado",
                   agent_id=self.agent_id,
                   service_info=self.stt_service.get_service_info())

    async def transcribe_audio(self, audio_path: str | Path, **kwargs) -> str:
        """
        Transcribe un archivo de audio a texto.

        Este es el método principal del agente que será llamado por otros agentes
        del sistema multiagente.

        Args:
            audio_path: Ruta al archivo de audio (string o Path)
            **kwargs: Parámetros adicionales para la transcripción (language, etc.)

        Returns:
            str: Texto transcrito

        Raises:
            STTServiceError: Error en la transcripción
            AudioFormatError: Formato de audio no soportado
        """
        # Convertir a Path si es necesario
        if isinstance(audio_path, str):
            audio_path = Path(audio_path)

        # Validar que el servicio esté disponible
        if not self.stt_service.is_service_available():
            raise STTServiceError(
                "Servicio STT no está disponible",
                self.stt_service.__class__.__name__
            )

        try:
            logger.info("Iniciando transcripción",
                       agent_id=self.agent_id,
                       audio_file=str(audio_path),
                       service=self.stt_service.__class__.__name__)

            # Realizar transcripción usando el servicio configurado
            transcribed_text = await self.stt_service.transcribe_audio(audio_path, **kwargs)

            # Registrar en el historial
            transcription_record = {
                "audio_file": str(audio_path),
                "transcribed_text": transcribed_text,
                "service_used": self.stt_service.__class__.__name__,
                "parameters": kwargs,
                "timestamp": asyncio.get_event_loop().time(),
                "success": True
            }
            self._transcription_history.append(transcription_record)

            logger.info("Transcripción completada exitosamente",
                       agent_id=self.agent_id,
                       text_preview=transcribed_text[:100] + "..." if len(transcribed_text) > 100 else transcribed_text,
                       text_length=len(transcribed_text))

            return transcribed_text

        except Exception as e:
            # Registrar error en el historial
            error_record = {
                "audio_file": str(audio_path),
                "error": str(e),
                "service_used": self.stt_service.__class__.__name__,
                "parameters": kwargs,
                "timestamp": asyncio.get_event_loop().time(),
                "success": False
            }
            self._transcription_history.append(error_record)

            logger.error("Error en transcripción",
                        agent_id=self.agent_id,
                        error=str(e),
                        audio_file=str(audio_path))

            # Re-lanzar la excepción para que el sistema multiagente pueda manejarla
            raise

    def get_supported_formats(self) -> list[str]:
        """
        Obtiene los formatos de audio soportados por el servicio actual.

        Returns:
            list[str]: Lista de extensiones de archivo soportadas
        """
        return self.stt_service.get_supported_formats()

    def get_service_info(self) -> Dict[str, Any]:
        """
        Obtiene información detallada sobre el agente y su servicio STT.

        Returns:
            Dict[str, Any]: Información del agente y servicio
        """
        service_info = self.stt_service.get_service_info()
        return {
            "agent_id": self.agent_id,
            "agent_type": "Speech-to-Text Agent",
            "service_info": service_info,
            "supported_formats": self.get_supported_formats(),
            "transcription_count": len(self._transcription_history),
            "is_service_available": self.stt_service.is_service_available()
        }

    def get_transcription_history(self) -> list[Dict[str, Any]]:
        """
        Obtiene el historial de transcripciones realizadas por este agente.

        Útil para debugging, auditoría y optimización del sistema.

        Returns:
            list[Dict[str, Any]]: Lista de registros de transcripción
        """
        return self._transcription_history.copy()

    def clear_history(self) -> None:
        """Limpia el historial de transcripciones."""
        self._transcription_history.clear()
        logger.info("Historial de transcripciones limpiado", agent_id=self.agent_id)

    async def health_check(self) -> Dict[str, Any]:
        """
        Realiza una verificación de salud del agente.

        Returns:
            Dict[str, Any]: Estado de salud del agente
        """
        try:
            is_available = self.stt_service.is_service_available()
            service_info = self.stt_service.get_service_info()

            health_status = {
                "agent_id": self.agent_id,
                "status": "healthy" if is_available else "unhealthy",
                "service_available": is_available,
                "service_info": service_info,
                "transcription_count": len(self._transcription_history),
                "timestamp": asyncio.get_event_loop().time()
            }

            logger.info("Health check completado",
                       agent_id=self.agent_id,
                       status=health_status["status"])

            return health_status

        except Exception as e:
            logger.error("Error en health check", agent_id=self.agent_id, error=str(e))
            return {
                "agent_id": self.agent_id,
                "status": "error",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }

    @classmethod
    def create_from_config(cls, config_path: str = None, agent_id: str = "stt_agent_001") -> "VoiceflowSTTAgent":
        """
        Factory method para crear un agente desde configuración.

        Args:
            config_path: Ruta al archivo de configuración
            agent_id: ID del agente

        Returns:
            VoiceflowSTTAgent: Instancia configurada del agente
        """
        stt_service = STTServiceFactory.create_from_config(config_path)
        return cls(stt_service, agent_id)


def create_stt_agent(config_path: str = None, agent_id: str = "stt_agent_001") -> VoiceflowSTTAgent:
    """
    Convenience function to create an STT agent instance.

    Args:
        config_path: Path to configuration file
        agent_id: Agent identifier

    Returns:
        VoiceflowSTTAgent: Configured STT agent instance
    """
    return VoiceflowSTTAgent.create_from_config(config_path, agent_id)
