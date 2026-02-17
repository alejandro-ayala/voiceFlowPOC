# API Reference - VoiceFlow Tourism PoC

**Actualizado**: 9 de Febrero de 2026
**Base URL**: `http://localhost:8000/api/v1`

---

## Endpoints REST

### Health

#### `GET /api/v1/health/`
Estado general del sistema.

**Response** (200):
```json
{
  "status": "success",
  "message": "System operational",
  "system_health": "healthy",
  "components": {
    "backend_adapter": { "status": "operational" },
    "audio_service": { "status": "healthy" },
    "api_server": { "status": "healthy", "version": "1.0.0" }
  },
  "version": "1.0.0"
}
```

#### `GET /api/v1/health/backend`
Health check detallado del backend (LangChain agents).

#### `GET /api/v1/health/audio`
Health check detallado del servicio de audio (STT).

---

### Audio

#### `POST /api/v1/audio/transcribe`
Transcribe un archivo de audio a texto.

**Request**: `multipart/form-data`
- `audio_file` (UploadFile, requerido): Archivo de audio (WAV, MP3, M4A, WebM, OGG)
- `language` (string, opcional): Codigo de idioma. Default: `es-ES`

**Response** (200):
```json
{
  "success": true,
  "status": "success",
  "transcription": "Necesito una ruta accesible al museo",
  "confidence": 0.92,
  "language": "es-ES",
  "duration": 3.5,
  "processing_time": 1.2,
  "is_simulation": false
}
```

**Errores**:
- `400`: Archivo vacio o no proporcionado
- `422`: Error de procesamiento de audio
- `500`: Error interno

#### `POST /api/v1/audio/transcribe-async`
Inicia transcripcion asincrona.

**Request**: Igual que `/transcribe`

**Response** (200):
```json
{
  "success": true,
  "processing_id": "uuid",
  "status": "processing",
  "progress": 0.0,
  "estimated_time": 10.0
}
```

#### `GET /api/v1/audio/transcribe-status/{processing_id}`
Estado de transcripcion asincrona.

**Response** (200):
```json
{
  "success": true,
  "processing_id": "uuid",
  "status": "completed",
  "progress": 1.0,
  "result": {
    "transcription": "...",
    "confidence": 0.92,
    "language": "es-ES"
  }
}
```

#### `POST /api/v1/audio/validate`
Valida un archivo de audio sin transcribirlo.

**Request**: `multipart/form-data` con `audio_file`

**Response** (200):
```json
{
  "success": true,
  "valid": true,
  "format": "audio/wav",
  "duration": 3.5,
  "file_size": 112000,
  "sample_rate": 16000,
  "channels": 1
}
```

#### `POST /api/v1/audio/stream-config`
Configuracion para streaming de audio (futuro).

---

### Chat

#### `POST /api/v1/chat/message`
Envia un mensaje y obtiene respuesta del asistente de turismo.

**Request** (JSON):
```json
{
  "message": "Como llego al Museo del Prado en silla de ruedas?",
  "conversation_id": "conv_123",
  "session_id": "session_abc",
  "user_preferences": {
    "active_profile_id": "cultural"
  }
}
```

**Validaciones**:
- `message`: no vacio, max 1000 caracteres
- `user_preferences.active_profile_id`: opcional, debe existir en profile registry

**Response** (200):
```json
{
  "status": "success",
  "ai_response": "El Museo del Prado tiene acceso completo para sillas de ruedas...",
  "session_id": "session_abc",
  "processing_time": 2.3,
  "intent": "route_planning",
  "entities": {
    "location": "Madrid",
    "accessibility_requirement": "wheelchair"
  },
  "tourism_data": {
    "venue": {
      "name": "Museo del Prado",
      "type": "museum",
      "accessibility_score": 9.5,
      "facilities": ["wheelchair_accessible", "accessible_restrooms", "accessible_parking"],
      "opening_hours": {"monday": "10:00-20:00"}
    },
    "routes": [
      {
        "transport": "metro",
        "line": "L1",
        "duration": "15 minutos",
        "accessibility": "wheelchair_accessible",
        "steps": ["Tomar línea 1 dirección Pinar de Chamartín"]
      }
    ],
    "accessibility": {
      "level": "fully_accessible",
      "score": 9.5,
      "certification": "iso_21542",
      "facilities": ["elevator", "accessible_entrance", "adapted_restrooms"]
    }
  },
  "pipeline_steps": [
    {
      "name": "Natural Language Understanding",
      "tool": "nlu",
      "status": "completed",
      "duration_ms": 125,
      "summary": "Intent: route_planning, Entities: {location, accessibility_requirement}"
    },
    {
      "name": "Accessibility Assessment",
      "tool": "accessibility",
      "status": "completed",
      "duration_ms": 89,
      "summary": "Venue accessibility score: 9.5/10"
    }
  ]
}
```

#### `GET /api/v1/chat/conversation/{conversation_id}`
Obtiene historial de una conversacion.

#### `GET /api/v1/chat/conversations`
Lista todas las conversaciones (paginado).

**Query params**: `limit` (default 10), `offset` (default 0)

#### `DELETE /api/v1/chat/conversation/{conversation_id}`
Elimina una conversacion.

#### `POST /api/v1/chat/conversation/{conversation_id}/clear`
Limpia los mensajes de una conversacion sin eliminarla.

#### `POST /api/v1/chat/analyze-transcription`
Analiza un texto transcrito (delegado internamente a `/message`).

#### `GET /api/v1/chat/demo/responses`
Respuestas de ejemplo para testing del frontend.

---

## Pipeline STT (Speech-to-Text)

### Interfaces

Definidas en `shared/interfaces/stt_interface.py`:

```python
class STTServiceInterface(ABC):
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str
    def is_service_available(self) -> bool
    def get_supported_formats(self) -> list[str]
    def get_service_info(self) -> Dict[str, Any]
```

### Implementaciones

| Clase | Ubicacion | Descripcion |
|-------|-----------|-------------|
| `AzureSpeechService` | `integration/external_apis/azure_stt_client.py` | Azure Cognitive Services Speech |
| `WhisperLocalService` | `integration/external_apis/whisper_services.py` | Whisper local (modelo descargado) |
| `WhisperAPIService` | `integration/external_apis/whisper_services.py` | Whisper via API REST de OpenAI |

### Factory

Ubicacion: `integration/external_apis/stt_factory.py`

```python
from integration.external_apis.stt_factory import STTServiceFactory

# Crear desde configuracion (.env)
service = STTServiceFactory.create_from_config()

# Crear servicio especifico
service = STTServiceFactory.create_service("azure", subscription_key="key", region="westeurope")

# Registrar nuevo servicio
STTServiceFactory.register_service("custom_stt", MiServicioSTT)

# Listar servicios disponibles
services = STTServiceFactory.get_available_services()
# ['azure', 'whisper_local', 'whisper_api']
```

### Agent STT

Ubicacion: `integration/external_apis/stt_agent.py`

```python
from integration.external_apis.stt_agent import VoiceflowSTTAgent, create_stt_agent

# Crear agente (usa STTServiceFactory internamente)
agent = create_stt_agent()

# Transcribir
text = await agent.transcribe_audio("audio.wav", language="es-ES")

# Health check
health = await agent.health_check()

# Historial de transcripciones
history = agent.get_transcription_history()
```

---

## Excepciones

Definidas en `shared/exceptions/exceptions.py`:

| Excepcion | HTTP Status | Uso |
|-----------|-------------|-----|
| `AudioProcessingException` | 422 | Error al procesar audio |
| `BackendCommunicationException` | 503 | Error comunicando con LangChain/OpenAI |
| `ValidationException` | 400 | Validacion de input fallida |
| `ConfigurationException` | 500 | Configuracion incorrecta |
| `AuthenticationException` | 401 | Autenticacion fallida (futuro) |

Excepciones STT (en `shared/interfaces/stt_interface.py`):

| Excepcion | Uso |
|-----------|-----|
| `STTServiceError` | Error base de servicios STT |
| `AudioFormatError` | Formato de audio no soportado |
| `ServiceConfigurationError` | Configuracion incorrecta del servicio STT |

---

## Interfaces de aplicacion

Definidas en `shared/interfaces/interfaces.py`:

### `AudioProcessorInterface`
Implementada por: `application/services/audio_service.py::AudioService`

```python
async def validate_audio(self, audio_data: bytes, filename: str) -> bool
async def process_audio_file(self, audio_path: Path) -> str
async def get_supported_formats(self) -> List[str]
```

### `BackendInterface`
Implementada por: `application/orchestration/backend_adapter.py::LocalBackendAdapter`

```python
async def process_query(self, transcription: str, active_profile_id: Optional[str] = None) -> Dict[str, Any]
async def get_system_status(self) -> Dict[str, Any]
async def clear_conversation(self) -> bool
```

**Descripción:**
- `process_query()`: Procesa consulta del usuario opcionalmente con contexto de perfil activo
- `active_profile_id`: ID del perfil activo (si existe) para aplicar directives y ranking bias

### `ConversationInterface`
Implementada por: `application/services/conversation_service.py::ConversationService`

```python
async def add_message(self, user_message: str, ai_response: str, session_id: Optional[str] = None) -> str
async def get_conversation_history(self, session_id: Optional[str] = None) -> List[Dict]
async def clear_conversation(self, session_id: Optional[str] = None) -> bool
```

---

## Dependency Injection

Ubicacion: `shared/utils/dependencies.py`

Las funciones DI se usan con `fastapi.Depends()` en los endpoints:

```python
from shared.utils.dependencies import get_audio_processor, get_backend_adapter, get_conversation_service

@router.post("/transcribe")
async def transcribe(
    audio_service: AudioProcessorInterface = Depends(get_audio_processor)
):
    ...
```

| Funcion DI | Retorna | Implementacion |
|------------|---------|----------------|
| `get_audio_processor()` | `AudioProcessorInterface` | `AudioService` |
| `get_backend_adapter()` | `BackendInterface` | `LocalBackendAdapter` |
| `get_conversation_service()` | `ConversationInterface` | `ConversationService` |
