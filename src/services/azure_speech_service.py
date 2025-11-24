from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
import azure.cognitiveservices.speech as speechsdk
import structlog

from ..interfaces.stt_interface import STTServiceInterface, STTServiceError, AudioFormatError, ServiceConfigurationError

logger = structlog.get_logger(__name__)


class AzureSpeechService(STTServiceInterface):
    """
    Implementación del servicio STT usando Azure Cognitive Services Speech.
    
    Cumple con el principio de Responsabilidad Única (SRP) - solo maneja la transcripción
    con Azure Speech Services.
    """
    
    SUPPORTED_FORMATS = ['wav', 'mp3', 'ogg', 'flac', 'm4a']
    
    def __init__(self, subscription_key: str, region: str):
        """
        Inicializa el servicio de Azure Speech.
        
        Args:
            subscription_key: Clave de suscripción de Azure
            region: Región de Azure (ej: 'eastus', 'westeurope')
        """
        self.subscription_key = subscription_key
        self.region = region
        self._speech_config = None
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Inicializa la configuración del servicio Azure Speech."""
        try:
            self._speech_config = speechsdk.SpeechConfig(
                subscription=self.subscription_key, 
                region=self.region
            )
            # Configuración para español (cambiable según necesidades)
            self._speech_config.speech_recognition_language = "es-ES"
            logger.info("Azure Speech Service inicializado correctamente", region=self.region)
        except Exception as e:
            raise ServiceConfigurationError(
                f"Error inicializando Azure Speech Service: {str(e)}",
                "azure_speech",
                e
            )
    
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str:
        """
        Transcribe un archivo de audio usando Azure Speech Services.
        
        Args:
            audio_path: Ruta al archivo de audio
            **kwargs: Parámetros adicionales (language, etc.)
            
        Returns:
            str: Texto transcrito
        """
        if not audio_path.exists():
            raise STTServiceError(
                f"Archivo de audio no encontrado: {audio_path}",
                "azure_speech"
            )
        
        if not self._is_supported_format(audio_path):
            raise AudioFormatError(
                f"Formato de audio no soportado: {audio_path.suffix}",
                "azure_speech"
            )
        
        try:
            # Configurar idioma si se proporciona
            language = kwargs.get('language', 'es-ES')
            self._speech_config.speech_recognition_language = language
            
            # Configurar audio input
            audio_input = speechsdk.audio.AudioConfig(filename=str(audio_path))
            
            # Crear recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self._speech_config,
                audio_config=audio_input
            )
            
            logger.info("Iniciando transcripción", audio_file=str(audio_path), language=language)
            
            # Realizar transcripción (Azure maneja esto de forma síncrona internamente)
            result = await self._recognize_once(speech_recognizer)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info("Transcripción completada exitosamente", 
                          text_length=len(result.text))
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No se pudo reconocer speech en el audio")
                return ""
            else:
                error_msg = f"Error en reconocimiento: {result.reason}"
                if result.cancellation_details:
                    error_msg += f" - {result.cancellation_details.reason}"
                raise STTServiceError(error_msg, "azure_speech")
                
        except Exception as e:
            if isinstance(e, STTServiceError):
                raise
            logger.error("Error en transcripción Azure", error=str(e))
            raise STTServiceError(
                f"Error durante la transcripción: {str(e)}",
                "azure_speech",
                e
            )
    
    async def _recognize_once(self, recognizer: speechsdk.SpeechRecognizer):
        """Wrapper asyncio para el método síncrono de Azure."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, recognizer.recognize_once)
    
    def _is_supported_format(self, audio_path: Path) -> bool:
        """Verifica si el formato de audio es soportado."""
        extension = audio_path.suffix.lower().lstrip('.')
        return extension in self.SUPPORTED_FORMATS
    
    def is_service_available(self) -> bool:
        """
        Verifica si el servicio está disponible realizando una prueba básica.
        """
        try:
            return self._speech_config is not None and bool(self.subscription_key)
        except Exception:
            return False
    
    def get_supported_formats(self) -> list[str]:
        """Retorna los formatos de audio soportados."""
        return self.SUPPORTED_FORMATS.copy()
    
    def get_service_info(self) -> Dict[str, Any]:
        """Retorna información del servicio."""
        return {
            "service_name": "Azure Cognitive Services Speech",
            "region": self.region,
            "supported_formats": self.get_supported_formats(),
            "default_language": "es-ES",
            "is_available": self.is_service_available()
        }
