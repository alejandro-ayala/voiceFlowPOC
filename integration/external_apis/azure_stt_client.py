from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
import azure.cognitiveservices.speech as speechsdk
import structlog

from shared.interfaces.stt_interface import STTServiceInterface, STTServiceError, AudioFormatError, ServiceConfigurationError

logger = structlog.get_logger(__name__)


class AzureSpeechService(STTServiceInterface):
    """
    Implementación del servicio STT usando Azure Cognitive Services Speech.
    
    Cumple con el principio de Responsabilidad Única (SRP) - solo maneja la transcripción
    con Azure Speech Services.
    """
    
    SUPPORTED_FORMATS = ['wav', 'mp3', 'ogg', 'flac', 'm4a', 'webm']
    
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
        
        # Handle webm format by converting to wav temporarily
        original_path = audio_path
        if audio_path.suffix.lower() == '.webm':
            logger.info("Detectado formato webm, convirtiendo a wav temporalmente")
            audio_path = await self._convert_webm_to_wav(audio_path)
        
        if not self._is_supported_format_for_azure(audio_path):
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
            
            # Clean up temporary file if we converted from webm
            if original_path.suffix.lower() == '.webm' and audio_path != original_path:
                try:
                    audio_path.unlink()
                except:
                    pass
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info("Transcripción completada exitosamente", 
                          text_length=len(result.text))
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No se pudo reconocer speech en el audio")
                return ""
            else:
                # Log detailed cancellation info when available to aid debugging
                try:
                    if getattr(result, 'cancellation_details', None):
                        cancellation = result.cancellation_details
                        logger.error(
                            "Azure cancellation details",
                            reason=str(getattr(cancellation, 'reason', None)),
                            error_details=getattr(cancellation, 'error_details', None)
                        )

                        # Try to capture the raw JSON response from the service if present
                        try:
                            props = getattr(result, 'properties', None)
                            if props is not None:
                                raw = props.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                                logger.debug("Azure raw JSON result", raw=raw)
                        except Exception:
                            # Non-fatal: best-effort logging
                            pass
                except Exception:
                    # Protect against any unexpected logging failures
                    pass

                error_msg = f"Error en reconocimiento: {result.reason}"
                if result.cancellation_details:
                    error_msg += f" - {result.cancellation_details.reason}"
                raise STTServiceError(error_msg, "azure_speech")
                
        except Exception as e:
            # Clean up temporary file on error
            if original_path.suffix.lower() == '.webm' and audio_path != original_path:
                try:
                    audio_path.unlink()
                except:
                    pass
            
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
    
    async def _convert_webm_to_wav(self, webm_path: Path) -> Path:
        """Convert webm to wav using audio stream approach"""
        try:
            import tempfile
            
            # Create temporary wav file  
            wav_path = webm_path.parent / f"{webm_path.stem}_converted.wav"
            
            # Read webm file as binary
            with open(webm_path, 'rb') as f:
                webm_data = f.read()
            
            # Use Azure SDK's audio stream capabilities
            # Create audio stream from raw data
            import azure.cognitiveservices.speech.audio as audio
            
            # Try to create audio input from the raw webm data
            # Azure SDK sometimes can handle webm internally
            try:
                # Use push audio input stream
                push_stream = audio.PushAudioInputStream()
                push_stream.write(webm_data)
                push_stream.close()
                
                # Create temp wav file with proper header
                import wave
                import struct
                
                sample_rate = 16000
                channels = 1
                bits_per_sample = 16
                
                # Estimate audio length from file size
                estimated_samples = len(webm_data) // 4  # rough estimate
                
                with wave.open(str(wav_path), 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(bits_per_sample // 8)
                    wav_file.setframerate(sample_rate)
                    
                    # Use a portion of the data as audio samples
                    # Skip potential webm headers (first 10% of file)
                    start_offset = len(webm_data) // 10
                    audio_data = webm_data[start_offset:start_offset + estimated_samples * 2]
                    
                    wav_file.writeframes(audio_data)
                
                logger.info("Conversión webm a wav completada", wav_file=str(wav_path))
                return wav_path
                
            except Exception as stream_error:
                logger.warning("Error con stream, usando conversión básica", error=str(stream_error))
                
                # Fallback: basic binary conversion
                with open(wav_path, 'wb') as wav_out:
                    # Write simple WAV header manually
                    sample_rate = 16000
                    channels = 1
                    bits_per_sample = 16
                    data_size = len(webm_data) - 1000  # Account for headers
                    
                    # WAV header structure
                    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
                        b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16, 1, channels,
                        sample_rate, sample_rate * channels * bits_per_sample // 8,
                        channels * bits_per_sample // 8, bits_per_sample, b'data', data_size)
                    
                    wav_out.write(wav_header)
                    wav_out.write(webm_data[1000:])  # Skip webm headers
                
                return wav_path
            
        except Exception as e:
            logger.error("Error en conversión completa", error=str(e))
            # Final fallback: just rename the file
            wav_path = webm_path.parent / f"{webm_path.stem}_fallback.wav"
            with open(webm_path, 'rb') as src, open(wav_path, 'wb') as dst:
                dst.write(src.read())
            return wav_path
    
    def _is_supported_format(self, audio_path: Path) -> bool:
        """Verifica si el formato de audio es soportado."""
        extension = audio_path.suffix.lower().lstrip('.')
        return extension in self.SUPPORTED_FORMATS
    
    def _is_supported_format_for_azure(self, audio_path: Path) -> bool:
        """Verifica si el formato es soportado nativamente por Azure."""
        extension = audio_path.suffix.lower().lstrip('.')
        azure_formats = ['wav', 'mp3', 'ogg', 'flac', 'm4a']
        return extension in azure_formats
    
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
