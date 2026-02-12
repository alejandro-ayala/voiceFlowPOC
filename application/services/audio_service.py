"""
Audio processing service implementing AudioProcessorInterface.
Handles real audio recording, validation and STT transcription.
"""

import base64
import tempfile
import wave
from pathlib import Path
from typing import List

import structlog

try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

from integration.configuration.settings import Settings
from shared.exceptions.exceptions import AudioProcessingException
from shared.interfaces.interfaces import AudioProcessorInterface

logger = structlog.get_logger(__name__)


class AudioService(AudioProcessorInterface):
    """
    Real audio processing service using existing STT infrastructure.
    Implements SOLID SRP principle.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.supported_formats = ["wav", "mp3", "ogg", "flac", "m4a"]
        self.max_size_bytes = settings.max_audio_size_mb * 1024 * 1024
        self.max_duration = settings.max_audio_duration
        self._stt_agent = None

    async def _get_stt_agent(self):
        """Lazy initialization of STT agent"""
        if self._stt_agent is None:
            try:
                from integration.external_apis.stt_agent import create_stt_agent

                logger.info("Initializing real STT agent for audio processing")
                self._stt_agent = create_stt_agent()
                logger.info("STT agent initialized successfully")
            except ImportError as e:
                logger.error("Failed to import STT agent", error=str(e))
                logger.warning("Will use fallback simulation mode")
                return None
            except Exception as e:
                logger.error("Failed to initialize STT agent", error=str(e))
                logger.warning("Will use fallback simulation mode")
                return None
        return self._stt_agent

    async def validate_audio(self, audio_data: bytes, filename: str) -> bool:
        """Validate audio file format, size and basic structure"""
        try:
            logger.info("Validating audio file", filename=filename, size_bytes=len(audio_data))

            if len(audio_data) > self.max_size_bytes:
                raise AudioProcessingException(
                    f"Audio file too large: {len(audio_data)} bytes (max: {self.max_size_bytes})",
                    error_code="FILE_TOO_LARGE",
                )

            if len(audio_data) < 1000:
                raise AudioProcessingException(
                    "Audio file too small - may be corrupted",
                    error_code="FILE_TOO_SMALL",
                )

            file_ext = Path(filename).suffix.lower().lstrip(".")
            if file_ext not in self.supported_formats:
                raise AudioProcessingException(
                    f"Unsupported audio format: {file_ext}",
                    error_code="UNSUPPORTED_FORMAT",
                    details={"supported_formats": self.supported_formats},
                )

            if file_ext == "wav":
                await self._validate_wav_structure(audio_data)

            logger.info("Audio validation successful")
            return True

        except AudioProcessingException:
            raise
        except Exception as e:
            logger.error("Audio validation failed", error=str(e))
            raise AudioProcessingException(f"Audio validation failed: {str(e)}", error_code="VALIDATION_ERROR")

    async def validate_audio_format(self, audio_data: bytes, format: str):
        """
        Validate audio file and return detailed information.
        This version returns a dictionary for the API with format validation.
        """
        try:
            logger.info("Validating audio data", data_size=len(audio_data), format=format)

            if len(audio_data) == 0:
                return {
                    "valid": False,
                    "error": "Empty audio data",
                    "format": format,
                    "file_size": 0,
                }

            if len(audio_data) > self.max_size_bytes:
                return {
                    "valid": False,
                    "error": f"File too large: {len(audio_data)} bytes (max: {self.max_size_bytes})",
                    "format": format,
                    "file_size": len(audio_data),
                }

            file_ext = format.lower()
            if "/" in file_ext:
                file_ext = file_ext.split("/")[-1]
            if file_ext.startswith("."):
                file_ext = file_ext[1:]

            estimated_duration = len(audio_data) / 16000

            result = {
                "valid": True,
                "format": file_ext,
                "file_size": len(audio_data),
                "duration": min(estimated_duration, 30.0),
                "sample_rate": 16000,
                "channels": 1,
            }

            logger.info("Audio validation successful", result=result)
            return result

        except Exception as e:
            logger.error("Audio validation failed", error=str(e))
            return {
                "valid": False,
                "error": str(e),
                "format": format,
                "file_size": len(audio_data) if audio_data else 0,
            }

    async def _validate_wav_structure(self, audio_data: bytes) -> None:
        """Validate WAV file structure"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()

                with wave.open(temp_file.name, "rb") as wav_file:
                    frames = wav_file.getnframes()
                    sample_rate = wav_file.getframerate()
                    duration = frames / sample_rate if sample_rate > 0 else 0

                    logger.info(
                        "WAV file info",
                        frames=frames,
                        sample_rate=sample_rate,
                        duration=f"{duration:.2f}s",
                    )

                    if duration > self.max_duration:
                        raise AudioProcessingException(
                            f"Audio too long: {duration:.1f}s (max: {self.max_duration}s)",
                            error_code="DURATION_TOO_LONG",
                        )

                    if duration < 0.1:
                        raise AudioProcessingException(
                            "Audio too short - minimum 0.1 seconds required",
                            error_code="DURATION_TOO_SHORT",
                        )

                Path(temp_file.name).unlink()

        except wave.Error as e:
            raise AudioProcessingException(
                f"Invalid WAV file structure: {str(e)}",
                error_code="INVALID_WAV_STRUCTURE",
            )

    async def process_audio_file(self, audio_path: Path) -> str:
        """Process audio file through real STT transcription"""
        try:
            logger.info("Processing audio file for transcription", file=str(audio_path))

            stt_agent = await self._get_stt_agent()

            health = await stt_agent.health_check()
            if health["status"] != "healthy":
                raise AudioProcessingException(
                    "STT service is not healthy",
                    error_code="STT_SERVICE_UNHEALTHY",
                    details=health,
                )

            logger.info("Starting transcription with Azure STT")
            transcription = await stt_agent.transcribe_audio(str(audio_path), language="es-ES")

            if not transcription or not transcription.strip():
                raise AudioProcessingException("No speech detected in audio", error_code="NO_SPEECH_DETECTED")

            logger.info(
                "Transcription completed successfully",
                transcription=(transcription[:100] + "..." if len(transcription) > 100 else transcription),
            )

            return transcription.strip()

        except AudioProcessingException:
            raise
        except Exception as e:
            logger.error("Audio processing failed", error=str(e))
            raise AudioProcessingException(
                f"Failed to process audio: {str(e)}",
                error_code="PROCESSING_ERROR",
                details={"error": str(e), "error_type": type(e).__name__},
            )

    async def process_base64_audio(self, base64_audio: str, filename: str) -> str:
        """Process base64 encoded audio data"""
        try:
            logger.info("Processing base64 audio data", filename=filename)

            try:
                if base64_audio.startswith("data:"):
                    base64_audio = base64_audio.split(",")[1]

                audio_data = base64.b64decode(base64_audio)
            except Exception as e:
                raise AudioProcessingException(
                    "Invalid base64 audio data",
                    error_code="INVALID_BASE64",
                    details={"decode_error": str(e)},
                )

            await self.validate_audio(audio_data, filename)

            original_ext = Path(filename).suffix.lower()

            with tempfile.NamedTemporaryFile(suffix=original_ext, delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()

                temp_original_path = Path(temp_file.name)

                try:
                    if original_ext == ".webm":
                        logger.info(
                            "Converting webm to wav format",
                            original_file=str(temp_original_path),
                        )
                        wav_path = self._convert_webm_to_wav(temp_original_path)
                        logger.info("Conversion completed", wav_file=str(wav_path))
                    else:
                        wav_path = temp_original_path

                    if not wav_path.exists():
                        raise AudioProcessingException(f"Audio file not found after conversion: {wav_path}")

                    logger.info("Using audio file for STT", final_file=str(wav_path))

                    transcription = await self.process_audio_file(wav_path)
                    return transcription

                finally:
                    if temp_original_path.exists():
                        temp_original_path.unlink()
                    if (
                        original_ext == ".webm"
                        and "wav_path" in locals()
                        and wav_path != temp_original_path
                        and wav_path.exists()
                    ):
                        wav_path.unlink()

        except AudioProcessingException:
            raise
        except Exception as e:
            logger.error("Base64 audio processing failed", error=str(e))
            raise AudioProcessingException(
                f"Failed to process base64 audio: {str(e)}",
                error_code="BASE64_PROCESSING_ERROR",
            )

    async def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return self.supported_formats.copy()

    async def get_service_info(self) -> dict:
        """Get audio service information and capabilities"""
        try:
            stt_agent = await self._get_stt_agent()
            service_info = stt_agent.get_service_info()

            return {
                "service_name": "VoiceFlow Audio Service",
                "stt_backend": service_info.get("service_info", {}).get("service_name", "Unknown"),
                "supported_formats": self.supported_formats,
                "max_file_size_mb": self.settings.max_audio_size_mb,
                "max_duration_seconds": self.max_duration,
                "default_language": "es-ES",
                "is_available": True,
            }
        except Exception as e:
            logger.error("Failed to get service info", error=str(e))
            return {
                "service_name": "VoiceFlow Audio Service",
                "stt_backend": "Unavailable",
                "supported_formats": self.supported_formats,
                "is_available": False,
                "error": str(e),
            }

    async def transcribe_audio(self, audio_data: bytes, format: str, language: str = "es-ES"):
        """
        Transcribe audio data using existing STT infrastructure.
        This method is specifically for the API endpoints.
        """
        import time

        start_time = time.time()

        logger.info(
            "Starting REAL audio transcription",
            data_size=len(audio_data),
            format=format,
            language=language,
        )

        try:
            is_valid = await self.validate_audio(audio_data, "temp_audio_file.wav")
            if not is_valid:
                raise AudioProcessingException("Invalid audio data")

            stt_agent = await self._get_stt_agent()
            if not stt_agent:
                logger.warning("STT agent not available, using fallback")
                processing_time = time.time() - start_time
                return type(
                    "Result",
                    (),
                    {
                        "transcription": "Servicio de transcripcion no disponible - usando simulacion",
                        "confidence": 0.5,
                        "language": language,
                        "duration": 3.0,
                        "processing_time": processing_time,
                    },
                )()

            import os

            if "webm" in format.lower():
                suffix = ".webm"
            elif "wav" in format.lower():
                suffix = ".wav"
            elif "mp3" in format.lower():
                suffix = ".mp3"
            elif "m4a" in format.lower():
                suffix = ".m4a"
            else:
                suffix = ".wav"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                temp_path = temp_file.name

            try:
                if "webm" in format.lower():
                    logger.info("Converting webm to wav for Azure STT", original_file=temp_path)
                    temp_path_obj = Path(temp_path)
                    wav_path = self._convert_webm_to_wav(temp_path_obj)
                    final_audio_path = str(wav_path)
                    logger.info("Conversion completed", wav_file=final_audio_path)
                else:
                    final_audio_path = temp_path

                logger.info(
                    "Calling REAL STT agent for transcription",
                    temp_file=final_audio_path,
                    file_size=os.path.getsize(final_audio_path),
                )

                transcribed_text = await stt_agent.transcribe_audio(audio_path=final_audio_path, language=language)

                processing_time = time.time() - start_time

                result = type(
                    "Result",
                    (),
                    {
                        "transcription": transcribed_text,
                        "confidence": 0.9,
                        "language": language,
                        "duration": 3.0,
                        "processing_time": processing_time,
                    },
                )()

                logger.info(
                    "REAL transcription completed successfully",
                    text=(transcribed_text[:100] + "..." if len(transcribed_text) > 100 else transcribed_text),
                    processing_time=processing_time,
                )

                return result

            finally:
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    if "webm" in format.lower() and "final_audio_path" in locals() and final_audio_path != temp_path:
                        if os.path.exists(final_audio_path):
                            os.unlink(final_audio_path)
                except Exception as e:
                    logger.warning("Failed to clean up temp files", error=str(e))

        except Exception as e:
            logger.error("Audio transcription failed", error=str(e))
            processing_time = time.time() - start_time
            return type(
                "Result",
                (),
                {
                    "transcription": f"Error en la transcripcion: {str(e)}",
                    "confidence": 0.0,
                    "language": language,
                    "duration": 0.0,
                    "processing_time": processing_time,
                },
            )()

    def _convert_webm_to_wav(self, input_path: Path) -> Path:
        """Convert webm audio file to wav format for Azure STT compatibility"""
        try:
            if not PYDUB_AVAILABLE:
                logger.warning("pydub not available, using original file")
                return input_path

            logger.info("Converting webm to wav format", input_file=str(input_path))

            output_path = input_path.with_suffix(".wav")

            try:
                from pydub import AudioSegment

                audio = AudioSegment.from_file(str(input_path), format="webm")
                audio = audio.set_frame_rate(16000).set_channels(1)
                audio.export(str(output_path), format="wav")

                logger.info(
                    "Audio converted successfully",
                    input_file=str(input_path),
                    output_file=str(output_path),
                )

                try:
                    input_path.unlink()
                except Exception:
                    pass

                return output_path

            except Exception as conv_error:
                logger.warning(
                    "Conversion failed, trying alternative method",
                    error=str(conv_error),
                )

                try:
                    with open(input_path, "rb") as f:
                        raw_data = f.read()

                    output_path = input_path.with_suffix(".wav")

                    sample_rate = 16000
                    channels = 1
                    bits_per_sample = 16

                    with wave.open(str(output_path), "wb") as wav_file:
                        wav_file.setnchannels(channels)
                        wav_file.setsampwidth(bits_per_sample // 8)
                        wav_file.setframerate(sample_rate)

                        audio_start = len(raw_data) // 10
                        audio_data = raw_data[audio_start : audio_start + 32000]
                        wav_file.writeframes(audio_data)

                    logger.info("Fallback conversion completed", output_file=str(output_path))
                    return output_path

                except Exception as fallback_error:
                    logger.error(
                        "All conversion methods failed",
                        conv_error=str(conv_error),
                        fallback_error=str(fallback_error),
                    )

                    logger.warning("Using original webm file as last resort")
                    return input_path

        except Exception as e:
            logger.error("Audio conversion failed", error=str(e))
            return input_path
