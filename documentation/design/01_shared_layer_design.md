# Software Design Document: Shared Layer

**Capa**: Cross-cutting concerns (`shared/`)
**Fecha**: 4 de Febrero de 2026
**Estado**: Implementado

---

## 1. Propósito

La capa `shared/` define los contratos (interfaces), excepciones y utilidades transversales que todas las demás capas consumen. No contiene lógica de negocio ni depende de ninguna otra capa del proyecto. Es el punto de acoplamiento mínimo que permite que las capas se comuniquen sin conocerse entre sí.

## 2. Componentes

### 2.1 Interfaces (`shared/interfaces/`)

#### 2.1.1 `interfaces.py` - Contratos entre capas

Define 5 interfaces abstractas (ABC) que establecen los contratos de servicio:

| Interfaz | Métodos | Implementada por | Estado |
|----------|---------|-------------------|--------|
| `AudioProcessorInterface` | `validate_audio()`, `process_audio_file()`, `get_supported_formats()` | `application/services/audio_service.py::AudioService` | Funcional |
| `BackendInterface` | `process_query()`, `get_system_status()`, `clear_conversation()` | `application/orchestration/backend_adapter.py::LocalBackendAdapter` | Funcional |
| `ConversationInterface` | `add_message()`, `get_conversation_history()`, `clear_conversation()` | `integration/data_persistence/conversation_repository.py::ConversationService` | Funcional |
| `AuthInterface` | `authenticate_user()`, `get_user_permissions()` | Ninguna | Sin implementar |
| `StorageInterface` | `save_conversation()`, `load_conversation()`, `delete_conversation()` | Ninguna | Sin implementar |

**Firmas detalladas:**

```python
class AudioProcessorInterface(ABC):
    async def validate_audio(self, audio_data: bytes, filename: str) -> bool
    async def process_audio_file(self, audio_path: Path) -> str
    async def get_supported_formats(self) -> List[str]

class BackendInterface(ABC):
    async def process_query(self, transcription: str) -> Dict[str, Any]
    async def get_system_status(self) -> Dict[str, Any]
    async def clear_conversation(self) -> bool

class ConversationInterface(ABC):
    async def add_message(self, user_message: str, ai_response: str) -> str
    async def get_conversation_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]
    async def clear_conversation(self, session_id: Optional[str] = None) -> bool

class AuthInterface(ABC):
    async def authenticate_user(self, token: str) -> Optional[Dict[str, Any]]
    async def get_user_permissions(self, user_id: str) -> List[str]

class StorageInterface(ABC):
    async def save_conversation(self, session_id: str, conversation: List[Dict[str, Any]]) -> bool
    async def load_conversation(self, session_id: str) -> Optional[List[Dict[str, Any]]]
    async def delete_conversation(self, session_id: str) -> bool
```

#### 2.1.2 `stt_interface.py` - Contrato STT

Define la interfaz específica para servicios de Speech-to-Text y su jerarquía de excepciones:

```python
class STTServiceInterface(ABC):
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str
    def is_service_available(self) -> bool
    def get_supported_formats(self) -> list[str]
    def get_service_info(self) -> Dict[str, Any]
```

**Jerarquía de excepciones STT:**

```
STTServiceError (base)
├── AudioFormatError       # Formato de audio no soportado
└── ServiceConfigurationError  # Configuración incorrecta del servicio
```

Cada excepción STT incluye: `message`, `service_name`, `original_error`.

**Implementaciones existentes:**

| Clase | Ubicación | Descripción |
|-------|-----------|-------------|
| `AzureSpeechService` | `integration/external_apis/azure_stt_client.py` | Azure Cognitive Services Speech |
| `WhisperLocalService` | `integration/external_apis/whisper_services.py` | OpenAI Whisper ejecutado localmente |
| `WhisperAPIService` | `integration/external_apis/whisper_services.py` | OpenAI Whisper vía API REST |

### 2.2 Excepciones (`shared/exceptions/`)

#### 2.2.1 `exceptions.py` - Jerarquía de excepciones del dominio

```
VoiceFlowException (base)
    message: str
    error_code: Optional[str]
    details: Optional[Dict[str, Any]]
    │
    ├── AudioProcessingException    # HTTP 422
    ├── BackendCommunicationException  # HTTP 503
    ├── ValidationException          # HTTP 400
    ├── ConfigurationException       # HTTP 500
    └── AuthenticationException      # HTTP 401
```

**Mapeo HTTP (`EXCEPTION_STATUS_CODES`):**

```python
EXCEPTION_STATUS_CODES = {
    AudioProcessingException: 422,
    BackendCommunicationException: 503,
    ValidationException: 400,
    ConfigurationException: 500,
    AuthenticationException: 401,
    VoiceFlowException: 500,  # fallback
}
```

Este diccionario es consumido por el exception handler global en `presentation/fastapi_factory.py` para convertir excepciones de dominio en respuestas HTTP con el status code correcto.

**Aliases de compatibilidad:**
- `AudioProcessingError` = `AudioProcessingException`
- `ValidationError` = `ValidationException`

### 2.3 Utilidades (`shared/utils/`)

#### 2.3.1 `dependencies.py` - Contenedor de Dependency Injection

Implementa el patrón DI usando `fastapi.Depends()`. Cada función devuelve una implementación concreta tipada contra su interfaz abstracta:

```python
def get_audio_processor(settings: Settings = Depends(get_settings)) -> AudioProcessorInterface:
    return AudioService(settings)

def get_backend_adapter(settings: Settings = Depends(get_settings)) -> BackendInterface:
    return LocalBackendAdapter(settings)

def get_conversation_service(settings: Settings = Depends(get_settings)) -> ConversationInterface:
    return ConversationService(settings)
```

**Funciones de lifecycle:**

```python
async def initialize_services()  # Llamado en app startup (lifespan)
async def cleanup_services()     # Llamado en app shutdown
```

**Observación:** `initialize_services()` crea instancias globales de los servicios además de las que crea el DI por request. Esto genera instancias duplicadas. Las variables globales (`_backend_service`, `_audio_service`, etc.) no se usan después de su creación.

**Clase auxiliar:** `SimulatedAudioService` - Servicio de audio simulado para demos sin Azure SDK. No implementa `AudioProcessorInterface` (no es compatible con la interfaz formal).

## 3. Diagrama de dependencias

```
shared/interfaces/interfaces.py ──> Solo depende de: abc, typing, pathlib (stdlib)
shared/interfaces/stt_interface.py ──> Solo depende de: abc, typing, pathlib (stdlib)
shared/exceptions/exceptions.py ──> Solo depende de: typing (stdlib)

shared/utils/dependencies.py ──> Depende de:
    ├── integration.configuration.settings (Settings, get_settings)
    ├── shared.interfaces.interfaces (las 3 interfaces activas)
    ├── application.orchestration.backend_adapter (LocalBackendAdapter)
    ├── application.services.audio_service (AudioService)
    └── application.services.conversation_service (ConversationService)
```

**Nota arquitectónica:** `dependencies.py` es el único archivo de `shared/` que rompe la independencia de capa, ya que importa directamente de `integration/` y `application/`. Esto es aceptable porque actúa como composition root del DI, pero idealmente debería moverse a `application/` o a raíz como un archivo de wiring.

## 4. Patrones de diseño

| Patrón | Componente | Descripción |
|--------|-----------|-------------|
| Interface Segregation (ISP) | `interfaces.py` | Cada interfaz es específica a un dominio funcional |
| Dependency Inversion (DIP) | `interfaces.py` + `dependencies.py` | Capas superiores dependen de abstracciones |
| Template Method | `STTServiceInterface` | Define esqueleto de transcripción, implementaciones concretas llenan los detalles |
| Composition Root | `dependencies.py` | Punto central donde se conectan interfaces con implementaciones |

## 5. Estrategia de testing

```python
# Test interfaces: verificar que las implementaciones cumplen el contrato
def test_audio_service_implements_interface():
    assert issubclass(AudioService, AudioProcessorInterface)

# Test excepciones: verificar mapeo HTTP
def test_exception_status_codes():
    assert EXCEPTION_STATUS_CODES[AudioProcessingException] == 422
    assert EXCEPTION_STATUS_CODES[ValidationException] == 400

# Test DI: verificar que las funciones devuelven las implementaciones correctas
def test_get_audio_processor_returns_audio_service():
    # Mock Settings, verificar tipo de retorno
```

## 6. Deuda técnica identificada

1. **`dependencies.py` ubicación**: Debería estar en `application/` como composition root, no en `shared/`
2. **`SimulatedAudioService`**: No implementa `AudioProcessorInterface`, debería hacerlo o eliminarse
3. **`initialize_services()` crea instancias duplicadas**: Las globals no se usan, el DI por request crea sus propias instancias
4. **`AuthInterface` y `StorageInterface`**: Definidas pero sin implementación en ninguna capa
5. **Inconsistencia en `ConversationInterface`**: La interfaz define `add_message(user, ai) -> str` pero la implementación en `conversation_repository.py` acepta `session_id` opcional como tercer parámetro
