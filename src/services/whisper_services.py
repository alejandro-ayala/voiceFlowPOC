from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
import structlog

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..interfaces.stt_interface import STTServiceInterface, STTServiceError, AudioFormatError, ServiceConfigurationError

logger = structlog.get_logger(__name__)


class WhisperLocalService(STTServiceInterface):
    """
    Implementación del servicio STT usando OpenAI Whisper en local.
    
    Cumple con el principio de Responsabilidad Única (SRP) - solo maneja la transcripción
    con Whisper local.
    """
    
    SUPPORTED_FORMATS = ['wav', 'mp3', 'ogg', 'flac', 'm4a', 'webm']
    AVAILABLE_MODELS = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
    
    def __init__(self, model_name: str = 'base'):
        """
        Inicializa el servicio Whisper local.
        
        Args:
            model_name: Nombre del modelo Whisper a usar
        """
        if not WHISPER_AVAILABLE:
            raise ServiceConfigurationError(
                "OpenAI Whisper no está instalado. Instale con: pip install openai-whisper",
                "whisper_local"
            )
        
        self.model_name = model_name
        self._model = None
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Inicializa y carga el modelo Whisper."""
        try:
            if self.model_name not in self.AVAILABLE_MODELS:
                raise ServiceConfigurationError(
                    f"Modelo no válido: {self.model_name}. Disponibles: {self.AVAILABLE_MODELS}",
                    "whisper_local"
                )
            
            logger.info("Cargando modelo Whisper", model=self.model_name)
            self._model = whisper.load_model(self.model_name)
            logger.info("Modelo Whisper cargado exitosamente")
            
        except Exception as e:
            raise ServiceConfigurationError(
                f"Error cargando modelo Whisper: {str(e)}",
                "whisper_local",
                e
            )
    
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str:
        """
        Transcribe un archivo de audio usando Whisper local.
        
        Args:
            audio_path: Ruta al archivo de audio
            **kwargs: Parámetros adicionales (language, task, etc.)
            
        Returns:
            str: Texto transcrito
        """
        if not audio_path.exists():
            raise STTServiceError(
                f"Archivo de audio no encontrado: {audio_path}",
                "whisper_local"
            )
        
        if not self._is_supported_format(audio_path):
            raise AudioFormatError(
                f"Formato de audio no soportado: {audio_path.suffix}",
                "whisper_local"
            )
        
        try:
            # Configurar opciones de transcripción
            options = {
                'language': kwargs.get('language', 'es'),  # español por defecto
                'task': kwargs.get('task', 'transcribe'),  # transcribe o translate
                'verbose': kwargs.get('verbose', False)
            }
            
            logger.info("Iniciando transcripción con Whisper local", 
                       audio_file=str(audio_path), 
                       options=options)
            
            # Ejecutar transcripción en un executor para no bloquear el loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self._model.transcribe(str(audio_path), **options)
            )
            
            transcribed_text = result.get('text', '').strip()
            
            logger.info("Transcripción completada exitosamente", 
                       text_length=len(transcribed_text))
            
            return transcribed_text
            
        except Exception as e:
            logger.error("Error en transcripción Whisper local", error=str(e))
            raise STTServiceError(
                f"Error durante la transcripción: {str(e)}",
                "whisper_local",
                e
            )
    
    def _is_supported_format(self, audio_path: Path) -> bool:
        """Verifica si el formato de audio es soportado."""
        extension = audio_path.suffix.lower().lstrip('.')
        return extension in self.SUPPORTED_FORMATS
    
    def is_service_available(self) -> bool:
        """Verifica si el servicio está disponible."""
        return WHISPER_AVAILABLE and self._model is not None
    
    def get_supported_formats(self) -> list[str]:
        """Retorna los formatos de audio soportados."""
        return self.SUPPORTED_FORMATS.copy()
    
    def get_service_info(self) -> Dict[str, Any]:
        """Retorna información del servicio."""
        return {
            "service_name": "OpenAI Whisper Local",
            "model": self.model_name,
            "supported_formats": self.get_supported_formats(),
            "available_models": self.AVAILABLE_MODELS,
            "is_available": self.is_service_available()
        }


class WhisperAPIService(STTServiceInterface):
    """
    Implementación del servicio STT usando OpenAI Whisper API.
    
    Cumple con el principio de Responsabilidad Única (SRP) - solo maneja la transcripción
    con Whisper API.
    """
    
    SUPPORTED_FORMATS = ['wav', 'mp3', 'ogg', 'flac', 'm4a', 'webm']
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB límite de OpenAI
    
    def __init__(self, api_key: str):
        """
        Inicializa el servicio Whisper API.
        
        Args:
            api_key: Clave de API de OpenAI
        """
        if not OPENAI_AVAILABLE:
            raise ServiceConfigurationError(
                "Cliente OpenAI no está instalado. Instale con: pip install openai",
                "whisper_api"
            )
        
        self.api_key = api_key
        self._client = None
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Inicializa el cliente de OpenAI."""
        try:
            self._client = openai.OpenAI(api_key=self.api_key)
            logger.info("Cliente OpenAI Whisper API inicializado correctamente")
        except Exception as e:
            raise ServiceConfigurationError(
                f"Error inicializando cliente OpenAI: {str(e)}",
                "whisper_api",
                e
            )
    
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str:
        """
        Transcribe un archivo de audio usando Whisper API.
        
        Args:
            audio_path: Ruta al archivo de audio
            **kwargs: Parámetros adicionales (language, etc.)
            
        Returns:
            str: Texto transcrito
        """
        if not audio_path.exists():
            raise STTServiceError(
                f"Archivo de audio no encontrado: {audio_path}",
                "whisper_api"
            )
        
        if not self._is_supported_format(audio_path):
            raise AudioFormatError(
                f"Formato de audio no soportado: {audio_path.suffix}",
                "whisper_api"
            )
        
        # Verificar tamaño del archivo
        file_size = audio_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            raise STTServiceError(
                f"Archivo demasiado grande: {file_size / (1024*1024):.1f}MB. Máximo: 25MB",
                "whisper_api"
            )
        
        try:
            logger.info("Iniciando transcripción con Whisper API", 
                       audio_file=str(audio_path))
            
            # Ejecutar llamada API en un executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                audio_path,
                kwargs
            )
            
            transcribed_text = result.text.strip()
            
            logger.info("Transcripción completada exitosamente", 
                       text_length=len(transcribed_text))
            
            return transcribed_text
            
        except Exception as e:
            logger.error("Error en transcripción Whisper API", error=str(e))
            raise STTServiceError(
                f"Error durante la transcripción: {str(e)}",
                "whisper_api",
                e
            )
    
    def _transcribe_sync(self, audio_path: Path, kwargs: Dict[str, Any]):
        """Método síncrono para la transcripción API."""
        with open(audio_path, 'rb') as audio_file:
            return self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=kwargs.get('language', 'es'),
                response_format="text"
            )
    
    def _is_supported_format(self, audio_path: Path) -> bool:
        """Verifica si el formato de audio es soportado."""
        extension = audio_path.suffix.lower().lstrip('.')
        return extension in self.SUPPORTED_FORMATS
    
    def is_service_available(self) -> bool:
        """Verifica si el servicio está disponible."""
        return OPENAI_AVAILABLE and self._client is not None and bool(self.api_key)
    
    def get_supported_formats(self) -> list[str]:
        """Retorna los formatos de audio soportados."""
        return self.SUPPORTED_FORMATS.copy()
    
    def get_service_info(self) -> Dict[str, Any]:
        """Retorna información del servicio."""
        return {
            "service_name": "OpenAI Whisper API",
            "model": "whisper-1",
            "supported_formats": self.get_supported_formats(),
            "max_file_size_mb": self.MAX_FILE_SIZE / (1024*1024),
            "is_available": self.is_service_available()
        }
