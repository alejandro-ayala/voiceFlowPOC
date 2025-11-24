# API Reference - VoiceflowSTTAgent

## 📋 Índice

- [Interfaces](#interfaces)
- [Servicios STT](#servicios-stt)
- [Factory](#factory)
- [Agente Principal](#agente-principal)
- [Excepciones](#excepciones)
- [Ejemplos de Uso](#ejemplos-de-uso)

## Interfaces

### STTServiceInterface

Interfaz base para todos los servicios de Speech-to-Text.

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

class STTServiceInterface(ABC):
```

#### Métodos Abstractos

##### `transcribe_audio(audio_path: Path, **kwargs) -> str`
Transcribe un archivo de audio a texto.

**Parámetros:**
- `audio_path` (Path): Ruta al archivo de audio
- `**kwargs`: Parámetros específicos del servicio
  - `language` (str, opcional): Código de idioma (ej: "es-ES", "en-US")
  - `task` (str, opcional): "transcribe" o "translate" (solo Whisper)
  - `verbose` (bool, opcional): Logs detallados (solo Whisper)

**Retorna:**
- `str`: Texto transcrito

**Excepciones:**
- `STTServiceError`: Error general en transcripción
- `AudioFormatError`: Formato de audio no soportado

**Ejemplo:**
```python
text = await service.transcribe_audio(
    Path("audio.wav"), 
    language="es-ES"
)
```

##### `is_service_available() -> bool`
Verifica si el servicio está disponible y configurado.

**Retorna:**
- `bool`: True si disponible

**Ejemplo:**
```python
if service.is_service_available():
    # Proceder con transcripción
    pass
```

##### `get_supported_formats() -> list[str]`
Obtiene formatos de audio soportados.

**Retorna:**
- `list[str]`: Lista de extensiones (sin punto)

**Ejemplo:**
```python
formats = service.get_supported_formats()
# ['wav', 'mp3', 'm4a', 'flac']
```

##### `get_service_info() -> Dict[str, Any]`
Información detallada del servicio.

**Retorna:**
- `Dict[str, Any]`: Información del servicio

**Ejemplo:**
```python
info = service.get_service_info()
print(info["service_name"])  # "Azure Cognitive Services Speech"
```

## Servicios STT

### AzureSpeechService

Implementación para Azure Cognitive Services Speech.

```python
from src.services.azure_speech_service import AzureSpeechService

service = AzureSpeechService(
    subscription_key="your_key",
    region="eastus"
)
```

#### Constructor

**Parámetros:**
- `subscription_key` (str): Clave de suscripción Azure
- `region` (str): Región Azure (ej: "eastus", "westeurope")

#### Características Específicas

**Formatos soportados:**
- WAV, MP3, OGG, FLAC, M4A

**Idiomas por defecto:**
- Español: "es-ES"
- Configurable via parámetro `language`

**Ejemplo de uso:**
```python
service = AzureSpeechService("key", "region")
text = await service.transcribe_audio(
    Path("audio.wav"),
    language="en-US"  # Cambiar idioma
)
```

### WhisperLocalService

Implementación para OpenAI Whisper local.

```python
from src.services.whisper_services import WhisperLocalService

service = WhisperLocalService(model_name="base")
```

#### Constructor

**Parámetros:**
- `model_name` (str): Modelo Whisper a usar
  - Opciones: "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
  - Por defecto: "base"

#### Características Específicas

**Formatos soportados:**
- WAV, MP3, OGG, FLAC, M4A, WEBM

**Modelos disponibles:**
```python
# Velocidad vs Precisión
"tiny"     # Más rápido, menos preciso
"base"     # Balance recomendado
"small"    # Buena precisión
"medium"   # Mejor precisión
"large"    # Máxima precisión
"large-v2" # Versión mejorada
"large-v3" # Última versión
```

**Ejemplo de uso:**
```python
service = WhisperLocalService("large-v2")
text = await service.transcribe_audio(
    Path("audio.wav"),
    language="es",      # Idioma esperado
    task="transcribe",  # o "translate"
    verbose=True        # Logs detallados
)
```

### WhisperAPIService

Implementación para OpenAI Whisper API.

```python
from src.services.whisper_services import WhisperAPIService

service = WhisperAPIService(api_key="your_openai_key")
```

#### Constructor

**Parámetros:**
- `api_key` (str): Clave API de OpenAI

#### Características Específicas

**Limitaciones:**
- Tamaño máximo: 25MB por archivo
- Costo: ~$0.006 por minuto de audio

**Formatos soportados:**
- WAV, MP3, OGG, FLAC, M4A, WEBM

**Ejemplo de uso:**
```python
service = WhisperAPIService("sk-...")
text = await service.transcribe_audio(
    Path("audio.wav"),
    language="es"  # Idioma esperado
)
```

## Factory

### STTServiceFactory

Factory para crear servicios STT basado en configuración.

```python
from src.factory import STTServiceFactory
```

#### Métodos de Clase

##### `create_service(service_type: str, **kwargs) -> STTServiceInterface`
Crea un servicio específico.

**Parámetros:**
- `service_type` (str): Tipo de servicio
  - "azure": Azure Speech Services
  - "whisper_local": Whisper local
  - "whisper_api": Whisper API
- `**kwargs`: Parámetros específicos del servicio

**Ejemplo:**
```python
# Azure
service = STTServiceFactory.create_service(
    "azure",
    subscription_key="key",
    region="eastus"
)

# Whisper Local
service = STTServiceFactory.create_service(
    "whisper_local",
    model_name="base"
)

# Whisper API
service = STTServiceFactory.create_service(
    "whisper_api",
    api_key="sk-..."
)
```

##### `create_from_config(config_path: str = None) -> STTServiceInterface`
Crea servicio desde configuración (.env).

**Parámetros:**
- `config_path` (str, opcional): Ruta a archivo de configuración

**Variables de entorno requeridas:**
```env
# Servicio a usar
STT_SERVICE=azure  # o whisper_local, whisper_api

# Azure
AZURE_SPEECH_KEY=your_key
AZURE_SPEECH_REGION=eastus

# Whisper Local
WHISPER_MODEL=base

# Whisper API
OPENAI_API_KEY=sk-...
```

**Ejemplo:**
```python
# Lee .env automáticamente
service = STTServiceFactory.create_from_config()

# Archivo específico
service = STTServiceFactory.create_from_config("config/prod.env")
```

##### `register_service(name: str, service_class: Type[STTServiceInterface])`
Registra nuevo tipo de servicio.

**Parámetros:**
- `name` (str): Nombre del servicio
- `service_class` (Type): Clase que implementa STTServiceInterface

**Ejemplo:**
```python
class MiServicioSTT(STTServiceInterface):
    # ... implementación

STTServiceFactory.register_service("mi_servicio", MiServicioSTT)

# Ahora disponible
service = STTServiceFactory.create_service("mi_servicio", param="value")
```

##### `get_available_services() -> list[str]`
Lista servicios disponibles.

**Retorna:**
- `list[str]`: Nombres de servicios registrados

**Ejemplo:**
```python
services = STTServiceFactory.get_available_services()
# ['azure', 'whisper_local', 'whisper_api']
```

## Agente Principal

### VoiceflowSTTAgent

Agente principal que coordina la transcripción STT.

```python
from src.voiceflow_stt_agent import VoiceflowSTTAgent
```

#### Constructor

```python
def __init__(self, stt_service: STTServiceInterface, agent_id: str = "stt_agent_001")
```

**Parámetros:**
- `stt_service` (STTServiceInterface): Servicio STT a usar
- `agent_id` (str): Identificador único del agente

#### Métodos Principales

##### `transcribe_audio(audio_path: str | Path, **kwargs) -> str`
Método principal de transcripción.

**Parámetros:**
- `audio_path` (str | Path): Ruta al archivo de audio
- `**kwargs`: Parámetros para el servicio STT

**Retorna:**
- `str`: Texto transcrito

**Excepciones:**
- `STTServiceError`: Error en transcripción
- `AudioFormatError`: Formato no soportado

**Ejemplo:**
```python
agent = VoiceflowSTTAgent(service)
text = await agent.transcribe_audio(
    "audio.wav",
    language="es-ES"
)
```

##### `health_check() -> Dict[str, Any]`
Verificación de salud del agente.

**Retorna:**
- `Dict[str, Any]`: Estado del agente

**Campos del resultado:**
- `agent_id` (str): ID del agente
- `status` (str): "healthy", "unhealthy", "error"
- `service_available` (bool): Si el servicio está disponible
- `service_info` (dict): Información del servicio
- `transcription_count` (int): Número de transcripciones realizadas
- `timestamp` (float): Timestamp de la verificación

**Ejemplo:**
```python
health = await agent.health_check()
if health["status"] == "healthy":
    # Agente operativo
    pass
```

##### `get_service_info() -> Dict[str, Any]`
Información completa del agente.

**Retorna:**
- `Dict[str, Any]`: Información del agente y servicio

**Ejemplo:**
```python
info = agent.get_service_info()
print(f"Agente: {info['agent_id']}")
print(f"Servicio: {info['service_info']['service_name']}")
print(f"Transcripciones: {info['transcription_count']}")
```

##### `get_transcription_history() -> list[Dict[str, Any]]`
Historial de transcripciones.

**Retorna:**
- `list[Dict[str, Any]]`: Lista de registros de transcripción

**Campos por registro:**
- `audio_file` (str): Ruta del archivo procesado
- `transcribed_text` (str): Texto resultado (si exitoso)
- `error` (str): Mensaje de error (si falló)
- `service_used` (str): Servicio usado
- `parameters` (dict): Parámetros usados
- `timestamp` (float): Timestamp de la operación
- `success` (bool): Si fue exitosa

**Ejemplo:**
```python
history = agent.get_transcription_history()
for record in history:
    if record["success"]:
        print(f"✅ {record['audio_file']}: {record['transcribed_text'][:50]}...")
    else:
        print(f"❌ {record['audio_file']}: {record['error']}")
```

##### `clear_history()`
Limpia el historial de transcripciones.

**Ejemplo:**
```python
agent.clear_history()
```

##### `get_supported_formats() -> list[str]`
Formatos soportados por el servicio actual.

**Retorna:**
- `list[str]`: Lista de extensiones

**Ejemplo:**
```python
formats = agent.get_supported_formats()
print(f"Formatos: {', '.join(formats)}")
```

#### Métodos de Clase

##### `create_from_config(config_path: str = None, agent_id: str = "stt_agent_001") -> VoiceflowSTTAgent`
Factory method para crear agente desde configuración.

**Parámetros:**
- `config_path` (str, opcional): Ruta a configuración
- `agent_id` (str): ID del agente

**Ejemplo:**
```python
# Configuración por defecto (.env)
agent = VoiceflowSTTAgent.create_from_config()

# Configuración específica
agent = VoiceflowSTTAgent.create_from_config(
    "config/prod.env",
    "prod_agent_001"
)
```

## Excepciones

### STTServiceError

Excepción base para errores en servicios STT.

```python
class STTServiceError(Exception):
    def __init__(self, message: str, service_name: str, original_error: Optional[Exception] = None)
```

**Atributos:**
- `message` (str): Mensaje descriptivo
- `service_name` (str): Nombre del servicio que causó el error
- `original_error` (Exception, opcional): Excepción original

**Ejemplo de manejo:**
```python
try:
    text = await agent.transcribe_audio("audio.wav")
except STTServiceError as e:
    print(f"Error en {e.service_name}: {e.message}")
    if e.original_error:
        print(f"Error original: {e.original_error}")
```

### AudioFormatError

Excepción para formatos de audio no soportados.

```python
class AudioFormatError(STTServiceError):
    # Hereda de STTServiceError
```

**Ejemplo de manejo:**
```python
try:
    text = await agent.transcribe_audio("audio.xyz")
except AudioFormatError as e:
    print(f"Formato no soportado: {e.message}")
    print(f"Formatos válidos: {agent.get_supported_formats()}")
```

### ServiceConfigurationError

Excepción para errores de configuración.

```python
class ServiceConfigurationError(STTServiceError):
    # Hereda de STTServiceError
```

**Ejemplo de manejo:**
```python
try:
    agent = VoiceflowSTTAgent.create_from_config()
except ServiceConfigurationError as e:
    print(f"Error de configuración: {e.message}")
    print("Verifica tu archivo .env")
```

## Ejemplos de Uso

### Uso Básico

```python
import asyncio
from src.voiceflow_stt_agent import VoiceflowSTTAgent

async def main():
    # Crear agente desde configuración
    agent = VoiceflowSTTAgent.create_from_config()
    
    # Verificar estado
    health = await agent.health_check()
    print(f"Estado: {health['status']}")
    
    # Transcribir audio
    try:
        text = await agent.transcribe_audio("audio.wav")
        print(f"Transcripción: {text}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

### Uso Avanzado con Múltiples Servicios

```python
import asyncio
from src.factory import STTServiceFactory
from src.voiceflow_stt_agent import VoiceflowSTTAgent

async def compare_services():
    """Comparar precisión entre servicios STT."""
    audio_file = "test_audio.wav"
    
    # Crear servicios
    services = {
        "Azure": STTServiceFactory.create_service(
            "azure", 
            subscription_key="key", 
            region="eastus"
        ),
        "Whisper Local": STTServiceFactory.create_service(
            "whisper_local", 
            model_name="base"
        )
    }
    
    results = {}
    for name, service in services.items():
        if service.is_service_available():
            agent = VoiceflowSTTAgent(service, f"agent_{name}")
            try:
                text = await agent.transcribe_audio(audio_file)
                results[name] = text
            except Exception as e:
                results[name] = f"Error: {e}"
    
    # Mostrar resultados
    for service, result in results.items():
        print(f"{service}: {result}")

asyncio.run(compare_services())
```

### Manejo de Errores Completo

```python
import asyncio
from pathlib import Path
from src.voiceflow_stt_agent import VoiceflowSTTAgent
from src.interfaces.stt_interface import STTServiceError, AudioFormatError, ServiceConfigurationError

async def robust_transcription(audio_path: str):
    """Transcripción con manejo robusto de errores."""
    
    try:
        # Crear agente
        agent = VoiceflowSTTAgent.create_from_config()
        
        # Verificar archivo
        path = Path(audio_path)
        if not path.exists():
            print(f"❌ Archivo no existe: {audio_path}")
            return None
        
        # Verificar formato
        if path.suffix.lower().lstrip('.') not in agent.get_supported_formats():
            print(f"❌ Formato no soportado: {path.suffix}")
            print(f"Formatos válidos: {agent.get_supported_formats()}")
            return None
        
        # Verificar servicio
        health = await agent.health_check()
        if health["status"] != "healthy":
            print(f"❌ Servicio no disponible: {health}")
            return None
        
        # Transcribir
        print(f"🎵 Transcribiendo: {audio_path}")
        text = await agent.transcribe_audio(audio_path, language="es-ES")
        print(f"✅ Resultado: {text}")
        return text
        
    except ServiceConfigurationError as e:
        print(f"❌ Error de configuración: {e.message}")
        print("Verifica tu archivo .env")
        
    except AudioFormatError as e:
        print(f"❌ Error de formato: {e.message}")
        
    except STTServiceError as e:
        print(f"❌ Error del servicio {e.service_name}: {e.message}")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    
    return None

# Uso
asyncio.run(robust_transcription("ejemplos/audio_prueba.wav"))
```

### Integración con Sistema Multiagente

```python
import asyncio
from typing import Dict, Any
from src.voiceflow_stt_agent import VoiceflowSTTAgent

class MultiAgentSystem:
    """Ejemplo de integración en sistema multiagente."""
    
    def __init__(self):
        self.stt_agent = VoiceflowSTTAgent.create_from_config("stt_agent")
        self.agents = {"stt": self.stt_agent}
    
    async def process_voice_input(self, audio_path: str) -> Dict[str, Any]:
        """Procesar entrada de voz en el sistema multiagente."""
        
        # 1. Verificar agente STT
        health = await self.stt_agent.health_check()
        if health["status"] != "healthy":
            return {"error": "STT agent no disponible"}
        
        # 2. Transcribir audio
        try:
            transcription = await self.stt_agent.transcribe_audio(audio_path)
        except Exception as e:
            return {"error": f"Error en transcripción: {e}"}
        
        # 3. Enviar a otros agentes del sistema
        result = {
            "transcription": transcription,
            "audio_file": audio_path,
            "agent_used": self.stt_agent.agent_id,
            "next_agents": ["nlu_agent", "planning_agent"]  # Ejemplo
        }
        
        return result
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Estado de todos los agentes del sistema."""
        status = {}
        
        for name, agent in self.agents.items():
            if hasattr(agent, 'health_check'):
                health = await agent.health_check()
                status[name] = health["status"]
            else:
                status[name] = "unknown"
        
        return status

# Uso en sistema multiagente
async def main():
    system = MultiAgentSystem()
    
    # Verificar sistema
    status = await system.get_system_status()
    print(f"Estado del sistema: {status}")
    
    # Procesar entrada de voz
    result = await system.process_voice_input("user_input.wav")
    print(f"Resultado: {result}")

asyncio.run(main())
```
