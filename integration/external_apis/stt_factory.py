from typing import Dict, Any, Type
from pathlib import Path
import os
from dotenv import load_dotenv
import structlog

from shared.interfaces.stt_interface import STTServiceInterface, ServiceConfigurationError
from integration.external_apis.azure_stt_client import AzureSpeechService
from integration.external_apis.whisper_services import WhisperLocalService, WhisperAPIService

logger = structlog.get_logger(__name__)


class STTServiceFactory:
    """
    Factory para crear instancias de servicios STT.

    Implementa el patrón Factory y cumple con el principio Abierto/Cerrado (OCP) -
    abierto para extensión (nuevos servicios) y cerrado para modificación.
    """

    _service_registry: Dict[str, Type[STTServiceInterface]] = {
        'azure': AzureSpeechService,
        'whisper_local': WhisperLocalService,
        'whisper_api': WhisperAPIService
    }

    @classmethod
    def create_service(cls, service_type: str, **kwargs) -> STTServiceInterface:
        """
        Crea una instancia del servicio STT especificado.

        Args:
            service_type: Tipo de servicio ('azure', 'whisper_local', 'whisper_api')
            **kwargs: Argumentos específicos del servicio

        Returns:
            STTServiceInterface: Instancia del servicio STT

        Raises:
            ServiceConfigurationError: Si el servicio no está disponible o mal configurado
        """
        if service_type not in cls._service_registry:
            available = ', '.join(cls._service_registry.keys())
            raise ServiceConfigurationError(
                f"Servicio STT no soportado: {service_type}. Disponibles: {available}",
                "factory"
            )

        service_class = cls._service_registry[service_type]

        try:
            logger.info("Creando servicio STT", service_type=service_type)
            return service_class(**kwargs)
        except Exception as e:
            logger.error("Error creando servicio STT", service_type=service_type, error=str(e))
            raise ServiceConfigurationError(
                f"Error creando servicio {service_type}: {str(e)}",
                "factory",
                e
            )

    @classmethod
    def create_from_config(cls, config_path: str = None) -> STTServiceInterface:
        """
        Crea un servicio STT basado en la configuración del archivo .env

        Args:
            config_path: Ruta al archivo de configuración (opcional)

        Returns:
            STTServiceInterface: Instancia del servicio configurado
        """
        # Cargar configuración
        if config_path:
            load_dotenv(config_path)
        else:
            load_dotenv()

        service_type = os.getenv('STT_SERVICE', 'azure').lower()

        # Configurar parámetros según el tipo de servicio
        if service_type == 'azure':
            return cls._create_azure_service()
        elif service_type == 'whisper_local':
            return cls._create_whisper_local_service()
        elif service_type == 'whisper_api':
            return cls._create_whisper_api_service()
        else:
            raise ServiceConfigurationError(
                f"Tipo de servicio no reconocido en configuración: {service_type}",
                "factory"
            )

    @classmethod
    def _create_azure_service(cls) -> AzureSpeechService:
        """Crea servicio Azure Speech desde variables de entorno."""
        subscription_key = os.getenv('AZURE_SPEECH_KEY')
        region = os.getenv('AZURE_SPEECH_REGION')

        if not subscription_key or not region:
            raise ServiceConfigurationError(
                "Configuración Azure incompleta. Necesita AZURE_SPEECH_KEY y AZURE_SPEECH_REGION",
                "azure"
            )

        return cls.create_service('azure',
                                subscription_key=subscription_key,
                                region=region)

    @classmethod
    def _create_whisper_local_service(cls) -> WhisperLocalService:
        """Crea servicio Whisper local desde variables de entorno."""
        model_name = os.getenv('WHISPER_MODEL', 'base')
        return cls.create_service('whisper_local', model_name=model_name)

    @classmethod
    def _create_whisper_api_service(cls) -> WhisperAPIService:
        """Crea servicio Whisper API desde variables de entorno."""
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            raise ServiceConfigurationError(
                "Configuración OpenAI incompleta. Necesita OPENAI_API_KEY",
                "whisper_api"
            )

        return cls.create_service('whisper_api', api_key=api_key)

    @classmethod
    def register_service(cls, name: str, service_class: Type[STTServiceInterface]) -> None:
        """
        Registra un nuevo tipo de servicio STT.

        Permite extender la factory con nuevos servicios sin modificar el código existente.

        Args:
            name: Nombre del servicio
            service_class: Clase que implementa STTServiceInterface
        """
        cls._service_registry[name] = service_class
        logger.info("Nuevo servicio STT registrado", name=name)

    @classmethod
    def get_available_services(cls) -> list[str]:
        """Retorna la lista de servicios disponibles."""
        return list(cls._service_registry.keys())
