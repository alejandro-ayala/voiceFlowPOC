# Software Design Document: Integration Layer

**Capa**: APIs externas y datos (`integration/`)
**Fecha**: 4 de Febrero de 2026
**Estado**: Implementado

---

## 1. Propósito

La capa `integration/` encapsula toda comunicación con servicios externos (Azure Speech, OpenAI Whisper) y la persistencia de datos. Ninguna otra capa conoce los detalles de implementación de estos servicios; solo interactúan a través de las interfaces definidas en `shared/`.

## 2. Componentes

### 2.1 External APIs (`integration/external_apis/`)

#### 2.1.1 `azure_stt_client.py` - Cliente Azure Speech Services

**Clase:** `AzureSpeechService(STTServiceInterface)`

| Aspecto | Detalle |
|---------|---------|
| SDK | `azure.cognitiveservices.speech` |
| Formatos soportados | wav, mp3, ogg, flac, m4a, webm |
| Idioma por defecto | es-ES |
| Requiere | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` |

**Métodos principales:**

```python
class AzureSpeechService(STTServiceInterface):
    def __init__(self, subscription_key: str, region: str)
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str
    def is_service_available(self) -> bool
    def get_supported_formats(self) -> list[str]
    def get_service_info(self) -> Dict[str, Any]
```

**Flujo de transcripción:**

```
audio_path → _is_supported_format?
    ├── .webm → _convert_webm_to_wav() → audio temporal .wav
    └── otros → directo
→ SpeechConfig(key, region) + AudioConfig(filename)
→ SpeechRecognizer.recognize_once() [vía run_in_executor]
→ ResultReason.RecognizedSpeech → texto
→ ResultReason.NoMatch → ""
→ Otro → STTServiceError
```

**Conversión WebM:** Implementa conversión manual webm→wav con headers WAV escritos byte a byte. Incluye fallback en cascada si la conversión principal falla.

#### 2.1.2 `whisper_services.py` - Clientes Whisper

Contiene dos implementaciones de `STTServiceInterface`:

**`WhisperLocalService`** - Whisper ejecutado localmente:

```python
class WhisperLocalService(STTServiceInterface):
    def __init__(self, model_name: str = 'base')
    # Modelos: tiny, base, small, medium, large, large-v2, large-v3
    # Requiere: pip install openai-whisper
    # Usa run_in_executor para no bloquear el event loop
```

**`WhisperAPIService`** - Whisper vía API OpenAI:

```python
class WhisperAPIService(STTServiceInterface):
    def __init__(self, api_key: str)
    # Modelo: whisper-1
    # Límite: 25MB por archivo
    # Requiere: OPENAI_API_KEY
    # Usa run_in_executor para la llamada HTTP
```

**Manejo de dependencias opcionales:**
```python
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
```
Si la dependencia no está instalada, `is_service_available()` retorna `False` y el constructor lanza `ServiceConfigurationError`.

#### 2.1.3 `stt_factory.py` - Factory Pattern para STT

**Clase:** `STTServiceFactory`

```python
class STTServiceFactory:
    _service_registry = {
        'azure': AzureSpeechService,
        'whisper_local': WhisperLocalService,
        'whisper_api': WhisperAPIService
    }

    @classmethod
    def create_service(cls, service_type: str, **kwargs) -> STTServiceInterface

    @classmethod
    def create_from_config(cls, config_path: str = None) -> STTServiceInterface

    @classmethod
    def register_service(cls, name: str, service_class: Type[STTServiceInterface]) -> None

    @classmethod
    def get_available_services(cls) -> list[str]
```

**`create_from_config()`** lee variables de entorno:
- `STT_SERVICE` → tipo de servicio (default: `azure`)
- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` → para Azure
- `WHISPER_MODEL` → para Whisper local (default: `base`)
- `OPENAI_API_KEY` → para Whisper API

**Extensibilidad (OCP):** Nuevos backends STT se registran con `register_service()` sin modificar código existente.

#### 2.1.4 `stt_agent.py` - Agente STT con Fallback

**Clase:** `VoiceflowSTTAgent`

```python
class VoiceflowSTTAgent:
    def __init__(self, stt_service: STTServiceInterface, agent_id: str)
    async def transcribe_audio(self, audio_path: str | Path, **kwargs) -> str
    async def health_check(self) -> Dict[str, Any]
    def get_transcription_history(self) -> list[Dict[str, Any]]
```

**Responsabilidades:**
- Coordina la transcripción delegando al servicio STT inyectado
- Mantiene historial de transcripciones (in-memory, para auditoría)
- Valida disponibilidad del servicio antes de transcribir
- Health check del agente y su servicio subyacente

**Convenience function:**
```python
def create_stt_agent(config_path=None, agent_id="stt_agent_001") -> VoiceflowSTTAgent:
    # Crea agente usando STTServiceFactory.create_from_config()
```

### 2.2 Data Persistence (`integration/data_persistence/`)

#### 2.2.1 `conversation_repository.py` - Repositorio de Conversaciones

**Clase:** `ConversationService(ConversationInterface)`

**Nota sobre naming:** El archivo se llama `conversation_repository.py` pero la clase se llama `ConversationService`. Esto genera confusión con `application/services/conversation_service.py` que contiene otra clase `ConversationService`.

```python
class ConversationService(ConversationInterface):
    def __init__(self, settings: Settings)
    # Almacenamiento:
    #   self.conversations: Dict[str, List[Dict[str, Any]]]  # session_id → messages
    #   self.session_metadata: Dict[str, Dict[str, Any]]     # session_id → metadata

    async def add_message(self, user_message, ai_response, session_id=None) -> str
    async def get_conversation_history(self, session_id=None) -> List[Dict]
    async def clear_conversation(self, session_id=None) -> bool
    async def get_session_info(self, session_id) -> Optional[Dict]
    async def get_all_sessions(self) -> List[Dict]
    async def export_conversation(self, session_id, format="json") -> Optional[Dict]
```

**Limitaciones:**
- Almacenamiento in-memory (se pierde al reiniciar el servidor)
- No soporta concurrencia (sin locks para acceso simultáneo a `self.conversations`)
- Sin límite de conversaciones almacenadas (posible memory leak en uso prolongado)

### 2.3 Configuration (`integration/configuration/`)

#### 2.3.1 `settings.py` - Configuración Centralizada

**Clase:** `Settings(BaseSettings)` - Pydantic BaseSettings

```python
class Settings(BaseSettings):
    # Application
    app_name: str = "VoiceFlow Tourism PoC"
    version: str = "1.0.0"
    debug: bool = True

    # Server
    host: str = "localhost"
    port: int = 8000
    reload: bool = True

    # CORS
    cors_origins: list[str] = ["*"]
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    # Backend
    backend_timeout: int = 30
    max_audio_duration: int = 30
    max_audio_size_mb: int = 10
    use_real_agents: bool = True

    # Azure STT
    azure_speech_key: Optional[str] = None
    azure_speech_region: Optional[str] = None
    stt_service: str = "azure"
    whisper_model: str = "base"

    # OpenAI
    openai_api_key: Optional[str] = None

    # Future
    auth_enabled: bool = False
    database_enabled: bool = False
    database_url: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VOICEFLOW_",
        case_sensitive=False,
        extra="ignore"
    )
```

**Singleton:** `settings = Settings()` como variable global. `get_settings()` devuelve siempre la misma instancia.

**Funciones auxiliares:**
- `is_production()` → `not settings.debug`
- `is_azure_deployment()` → `settings.azure_webapp_name is not None`
- `get_cors_config()` → dict con configuración CORS (restrictiva en producción, permisiva en desarrollo)

## 3. Diagrama de clases

```
                    STTServiceInterface (shared/)
                    ┌──────────────────┐
                    │ transcribe_audio │
                    │ is_available     │
                    │ get_formats      │
                    │ get_info         │
                    └────────┬─────────┘
            ┌────────────────┼───────────────────┐
            │                │                   │
    AzureSpeechService  WhisperLocal       WhisperAPI
    (azure_stt_client)  (whisper_services)  (whisper_services)
            │                │                   │
            └────────────────┼───────────────────┘
                             │
                    STTServiceFactory ─── registry dict
                    (stt_factory.py)
                             │
                    VoiceflowSTTAgent
                    (stt_agent.py)
                             │
                    create_stt_agent() ── convenience function
```

## 4. Flujo de fallback STT

```
create_stt_agent()
    → STTServiceFactory.create_from_config()
        → Lee STT_SERVICE env var (default: "azure")
        → Intenta crear AzureSpeechService
            ├── OK → retorna agente con Azure
            └── FALLO (sin SDK o sin keys)
                → ServiceConfigurationError
                → AudioService._get_stt_agent() captura el error
                    → Retorna None
                    → transcribe_audio() usa fallback simulado
```

## 5. Variables de entorno requeridas

| Variable | Obligatoria | Default | Descripción |
|----------|-------------|---------|-------------|
| `AZURE_SPEECH_KEY` | Para Azure STT | None | API key de Azure Speech |
| `AZURE_SPEECH_REGION` | Para Azure STT | None | Región Azure (ej: westeurope) |
| `OPENAI_API_KEY` | Para Whisper API y LangChain | None | API key OpenAI |
| `STT_SERVICE` | No | "azure" | Backend STT (azure/whisper_local/whisper_api) |
| `WHISPER_MODEL` | No | "base" | Modelo Whisper local |

## 6. Estrategia de testing

```python
# Test Factory: verificar creación de servicios
def test_factory_creates_azure_service():
    service = STTServiceFactory.create_service('azure', subscription_key='test', region='test')
    assert isinstance(service, AzureSpeechService)

def test_factory_raises_on_unknown_service():
    with pytest.raises(ServiceConfigurationError):
        STTServiceFactory.create_service('unknown')

# Test Registry: verificar extensibilidad
def test_register_custom_service():
    STTServiceFactory.register_service('custom', MockSTTService)
    assert 'custom' in STTServiceFactory.get_available_services()

# Test Agent: verificar delegación y historial
def test_agent_records_transcription_history():
    mock_service = MockSTTService()
    agent = VoiceflowSTTAgent(mock_service)
    await agent.transcribe_audio(test_audio_path)
    assert len(agent.get_transcription_history()) == 1

# Test ConversationService: verificar CRUD
def test_add_and_retrieve_message():
    service = ConversationService(mock_settings)
    sid = await service.add_message("hola", "respuesta")
    history = await service.get_conversation_history(sid)
    assert len(history) == 1
```

## 7. Deuda técnica identificada

1. **Naming confuso:** `conversation_repository.py` contiene `ConversationService` - debería renombrarse a `ConversationRepository` o el archivo a `conversation_service.py`
2. **Sin concurrencia:** `ConversationService` no tiene locks para acceso concurrente a sus dicts
3. **Sin límite de memoria:** No hay TTL ni límite de conversaciones almacenadas
4. **Conversión WebM frágil:** `azure_stt_client.py` implementa conversión webm→wav con manipulación binaria directa que puede producir audio corrupto
5. **OpenAI no tiene cliente propio:** Se integra vía LangChain en business layer. Si se necesita OpenAI sin LangChain, no hay abstracción disponible
6. **`env_prefix="VOICEFLOW_"`:** Definido en Settings pero las variables de entorno documentadas no usan este prefijo (AZURE_SPEECH_KEY vs VOICEFLOW_AZURE_SPEECH_KEY). Funciona porque `extra="ignore"` y Pydantic también busca sin prefijo
