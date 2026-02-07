from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

class STTServiceInterface(ABC):
    """
    Interfaz abstracta para servicios de Speech-to-Text.
    
    Implementa el principio de Inversión de Dependencias (DIP) de SOLID,
    permitiendo que el agente STT dependa de abstracciones y no de implementaciones concretas.
    """
    
    @abstractmethod
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str:
        """
        Transcribe un archivo de audio a texto.
        
        Args:
            audio_path: Ruta al archivo de audio
            **kwargs: Parámetros adicionales específicos del servicio
            
        Returns:
            str: Texto transcrito
            
        Raises:
            STTServiceError: Error en la transcripción
        """
        pass
    
    @abstractmethod
    def is_service_available(self) -> bool:
        """
        Verifica si el servicio STT está disponible y configurado correctamente.
        
        Returns:
            bool: True si el servicio está disponible
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """
        Obtiene los formatos de audio soportados por el servicio.
        
        Returns:
            list[str]: Lista de extensiones de archivo soportadas
        """
        pass
    
    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre el servicio STT.
        
        Returns:
            Dict[str, Any]: Información del servicio (nombre, versión, configuración, etc.)
        """
        pass


class STTServiceError(Exception):
    """Excepción personalizada para errores en servicios STT."""
    
    def __init__(self, message: str, service_name: str, original_error: Optional[Exception] = None):
        self.message = message
        self.service_name = service_name
        self.original_error = original_error
        super().__init__(f"[{service_name}] {message}")


class AudioFormatError(STTServiceError):
    """Excepción para errores relacionados con formatos de audio no soportados."""
    pass


class ServiceConfigurationError(STTServiceError):
    """Excepción para errores de configuración del servicio STT."""
    pass
