# Software Design Document: Application Layer

**Capa**: APIs, servicios y orquestación (`application/`)
**Fecha**: 4 de Febrero de 2026
**Estado**: Implementado

---

## 1. Propósito

La capa `application/` implementa la API REST, los servicios de aplicación (audio, conversaciones) y la orquestación que conecta la presentation layer con la business layer. Contiene la lógica de coordinación sin contener lógica de dominio.

## 2. Componentes

### 2.1 API Endpoints (`application/api/v1/`)

#### 2.1.1 `audio.py` - API de Audio

**Router:** `APIRouter(prefix="/audio")`

| Endpoint | Método | Descripción | DI |
|----------|--------|-------------|-----|
| `/api/v1/audio/transcribe` | POST | Transcripción de audio (UploadFile) | `AudioProcessorInterface` |
| `/api/v1/audio/transcribe-async` | POST | Transcripción asíncrona (BackgroundTasks) | `AudioProcessorInterface` |
| `/api/v1/audio/transcribe-status/{id}` | GET | Estado de transcripción async | - |
| `/api/v1/audio/validate` | POST | Validación de audio sin transcribir | `AudioProcessorInterface` |
| `/api/v1/audio/stream-config` | POST | Config para streaming (futuro) | - |

**Flujo de `/transcribe`:**
```
UploadFile → audio_file.read() → audio_service.transcribe_audio(data, format, language)
    → Result(transcription, confidence, language, duration, processing_time)
    → JSON response
```

**Estado async:** `processing_status` dict in-memory (no compartido entre workers).

#### 2.1.2 `chat.py` - API de Chat

**Router:** `APIRouter(prefix="/chat")`

| Endpoint | Método | Descripción | DI |
|----------|--------|-------------|-----|
| `/api/v1/chat/message` | POST | Envía mensaje y obtiene respuesta IA | `BackendInterface`, `ConversationInterface` |
| `/api/v1/chat/conversation/{id}` | GET | Obtiene historial de conversación | `ConversationInterface` |
| `/api/v1/chat/conversations` | GET | Lista todas las conversaciones (paginado) | `ConversationInterface` |
| `/api/v1/chat/conversation/{id}` | DELETE | Elimina una conversación | `ConversationInterface` |
| `/api/v1/chat/conversation/{id}/clear` | POST | Limpia mensajes de una conversación | `ConversationInterface` |
| `/api/v1/chat/analyze-transcription` | POST | Analiza texto transcrito (delegado a `/message`) | `BackendInterface`, `ConversationInterface` |
| `/api/v1/chat/demo/responses` | GET | Respuestas demo para testing del UI | - |

**Flujo de `/message`:**
```
ChatMessageRequest → validate message
    → backend_service.process_query(message)     # Business layer
    → conversation_service.add_message(user, ai)  # Persistencia
    → ChatResponse(ai_response, session_id, processing_time, intent, entities)
```

#### 2.1.3 `health.py` - API de Health

**Router:** `APIRouter(prefix="/health")`

| Endpoint | Método | Descripción | DI |
|----------|--------|-------------|-----|
| `/api/v1/health/` | GET | Estado general del sistema | `BackendInterface`, `AudioProcessorInterface`, `Settings` |
| `/api/v1/health/backend` | GET | Health check detallado del backend | `BackendInterface` |
| `/api/v1/health/audio` | GET | Health check detallado del audio | - (crea stt_agent directamente) |

**Observación:** `/health/audio` no usa DI; importa y crea `create_stt_agent()` directamente, rompiendo el patrón DI del resto de endpoints.

### 2.2 Servicios (`application/services/`)

#### 2.2.1 `audio_service.py` - Servicio de Audio

**Clase:** `AudioService(AudioProcessorInterface)`

```python
class AudioService(AudioProcessorInterface):
    def __init__(self, settings: Settings)
    async def validate_audio(self, audio_data: bytes, filename: str) -> bool
    async def process_audio_file(self, audio_path: Path) -> str
    async def process_base64_audio(self, base64_audio: str, filename: str) -> str
    async def get_supported_formats(self) -> List[str]
    async def get_service_info(self) -> dict
    async def transcribe_audio(self, audio_data: bytes, format: str, language: str) -> Result

    # Internos
    async def _get_stt_agent(self) -> Optional[VoiceflowSTTAgent]  # Lazy init
    async def _validate_wav_structure(self, audio_data: bytes) -> None
    def _convert_webm_to_wav(self, input_path: Path) -> Path
```

**Responsabilidades:**
- Validación de audio (formato, tamaño, duración, estructura WAV)
- Conversión webm→wav (con fallback si pydub no disponible)
- Delegación de transcripción al STT agent
- Fallback a simulación si STT no disponible

**Flujo de fallback:**
```
_get_stt_agent()
    → create_stt_agent() [desde integration/]
    ├── OK → usa Azure/Whisper real
    └── ImportError/Exception → retorna None
        → transcribe_audio() retorna Result simulado
```

**Observación:** La clase tiene **dos métodos `validate_audio`** con firmas diferentes:
1. `validate_audio(self, audio_data: bytes, filename: str) -> bool` (interfaz)
2. `validate_audio(self, audio_data: bytes, format: str)` (dict return, para API)

El segundo sobreescribe al primero según el orden de definición en el archivo.

#### 2.2.2 `conversation_service.py` - Servicio de Conversaciones

**Nota:** Este archivo es idéntico a `integration/data_persistence/conversation_repository.py`. Ambos contienen la misma clase `ConversationService`. El DI en `dependencies.py` importa esta versión (`application/services/`).

### 2.3 Orquestación (`application/orchestration/`)

#### 2.3.1 `backend_adapter.py` - Adapter a Business Layer

**Clase:** `LocalBackendAdapter(BackendInterface)`

```python
class LocalBackendAdapter(BackendInterface):
    def __init__(self, settings: Settings)
    async def process_query(self, transcription: str) -> Dict[str, Any]
    async def get_system_status(self) -> Dict[str, Any]
    async def clear_conversation(self) -> bool

    # Internos
    async def _get_backend_instance(self)  # Lazy init de TourismMultiAgent
    async def _process_real_query(self, transcription: str) -> str
    async def _simulate_ai_response(self, transcription: str) -> str
```

**Logica de decision:**
```
process_query()
    ├── use_real_agents=True → _process_real_query()
    │   → TourismMultiAgent.process_request() → AgentResponse
    │   ├── OK → result.response_text (respuesta real GPT-4)
    │   └── Error → fallback a _simulate_ai_response()
    └── use_real_agents=False → _simulate_ai_response()
        → Respuestas hardcodeadas por keyword matching
```

**Contrato con Business Layer:** Desde la Fase 2B, el adapter usa directamente `MultiAgentInterface.process_request()` que retorna `AgentResponse(response_text, tool_results, metadata)`. Se elimino la cadena de `hasattr()` con 5 fallbacks.

**Simulacion:** `_simulate_ai_response()` contiene ~110 lineas de respuestas hardcodeadas en espanol sobre turismo accesible en Madrid.

**Observacion:** La logica de simulacion deberia estar en un servicio mock separado, no en el adapter.

### 2.4 Modelos (`application/models/`)

#### 2.4.1 `requests.py` - Modelos de Request

| Modelo | Campos principales | Validaciones |
|--------|-------------------|--------------|
| `AudioUploadRequest` | audio_data (base64), filename, content_type | filename no vacío, audio_data min 100 chars |
| `AudioTranscriptionRequest` | audio_data (base64), language, format | audio_data min 100 chars |
| `ChatMessageRequest` | message, conversation_id, session_id, timestamp, context | message no vacío, max 1000 chars |
| `SystemStatusRequest` | check_backend, check_services | - |
| `ConversationRequest` | session_id, action | action in [get, clear, export] |
| `ChatHistoryRequest` | conversation_id, limit, offset | limit 1-1000 |
| `ConversationCreateRequest` | topic, user_id, metadata | - |

#### 2.4.2 `responses.py` - Modelos de Response

```
BaseResponse
    status: StatusEnum (success/error/warning/info)
    message: str
    timestamp: datetime
    │
    ├── AudioProcessingResponse (transcription, confidence, duration, language)
    ├── AudioTranscriptionResponse (transcription, confidence, language, is_simulation)
    ├── AudioProcessingStatusResponse (processing_id, is_complete, progress)
    ├── ChatResponse (ai_response, session_id, processing_time, tourism_data, intent, entities)
    ├── SystemStatusResponse (system_health, components, uptime, version)
    ├── ConversationHistoryResponse (session_id, messages, total_messages)
    ├── ConversationResponse (conversation_id, messages, created_at, updated_at, message_count)
    ├── ConversationListResponse (conversations, total_count, limit, offset)
    └── ErrorResponse (error_code, details, suggestions)
```

## 3. Diagrama de dependencias

```
application/api/v1/audio.py
    → shared/interfaces (AudioProcessorInterface)
    → shared/utils/dependencies (get_audio_processor)
    → shared/exceptions (AudioProcessingError, ValidationError)
    → application/models/requests (AudioTranscriptionRequest)
    → application/models/responses (AudioTranscriptionResponse, ...)

application/api/v1/chat.py
    → shared/interfaces (BackendInterface, ConversationInterface)
    → shared/utils/dependencies (get_backend_adapter, get_conversation_service)
    → shared/exceptions (BackendCommunicationException, ValidationException)
    → application/models/requests (ChatMessageRequest, ChatHistoryRequest)
    → application/models/responses (ChatResponse, ConversationResponse, ...)

application/api/v1/health.py
    → shared/interfaces (BackendInterface, AudioProcessorInterface)
    → shared/utils/dependencies (get_backend_adapter, get_audio_processor)
    → integration/configuration/settings (get_settings, Settings)
    → application/models/responses (SystemStatusResponse, StatusEnum)

application/orchestration/backend_adapter.py
    → shared/interfaces (BackendInterface)
    → shared/exceptions (BackendCommunicationException)
    → integration/configuration/settings (Settings)
    → business/domains/tourism/agent (TourismMultiAgent) [lazy import]

application/services/audio_service.py
    → shared/interfaces (AudioProcessorInterface)
    → shared/exceptions (AudioProcessingException)
    → integration/configuration/settings (Settings)
    → integration/external_apis/stt_agent (create_stt_agent) [lazy import]
```

## 4. Patrones de diseño

| Patrón | Componente | Descripción |
|--------|-----------|-------------|
| Adapter | `LocalBackendAdapter` | Adapta TourismMultiAgent a BackendInterface |
| Dependency Injection | Todos los endpoints | Via `Depends()` de FastAPI |
| Lazy Initialization | `AudioService._get_stt_agent()`, `LocalBackendAdapter._get_backend_instance()` | Retrasa imports pesados |
| Fallback/Graceful Degradation | `AudioService`, `LocalBackendAdapter` | Simulación cuando servicios reales no disponibles |
| DTO | `requests.py`, `responses.py` | Pydantic models para validación y serialización |

## 5. Estrategia de testing

```python
# Test endpoints con TestClient (ya hay fixture en conftest.py)
def test_health_endpoint(test_client):
    response = test_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json()["status"] in ["success", "warning", "error"]

def test_chat_message_empty_rejected(test_client):
    response = test_client.post("/api/v1/chat/message", json={"message": ""})
    assert response.status_code == 422  # Pydantic validation

def test_demo_responses(test_client):
    response = test_client.get("/api/v1/chat/demo/responses")
    assert response.status_code == 200
    assert "sample_responses" in response.json()

# Test servicios con mocks
def test_audio_service_fallback_when_no_stt():
    service = AudioService(mock_settings)
    # Sin Azure SDK, debe retornar resultado simulado
    result = await service.transcribe_audio(b"audio_data", "wav")
    assert result.confidence == 0.5  # Fallback confidence

def test_backend_adapter_simulation_mode():
    settings = Settings(use_real_agents=False)
    adapter = LocalBackendAdapter(settings)
    result = await adapter.process_query("museo del prado")
    assert "Prado" in result["ai_response"]
```

## 6. Deuda técnica identificada

1. **`AudioService.validate_audio` duplicado:** Dos métodos con la misma firma pero return types distintos (bool vs dict)
2. **`conversation_service.py` duplicado:** Copia exacta de `integration/data_persistence/conversation_repository.py`
3. **`/health/audio` rompe DI:** Crea `create_stt_agent()` directamente en vez de usar `Depends()`
4. **Simulación en adapter:** `_simulate_ai_response()` (~110 líneas de texto hardcoded) no pertenece al adapter
5. ~~**Reflection en `_process_real_query`:**~~ Resuelto en Fase 2B - usa contrato directo `process_request() -> AgentResponse`
6. **`processing_status` global:** Dict in-memory para async transcription, no compartido entre workers uvicorn
7. **`ChatResponse.entities`:** Tipado como `Optional[Dict[str, Any]]` pero el frontend espera `Optional[List[str]]` según la documentación API
8. **Response models parcialmente usados:** Algunos endpoints retornan dicts directos en vez de usar los response models definidos
