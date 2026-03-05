# Software Design Document: Integration Layer

**Capa**: APIs externas y datos (`integration/`)
**Fecha**: 5 de Marzo de 2026
**Estado**: Implementado (actualizado Post Fase 0 + Fase 1)

---

## 1. Propósito

La capa `integration/` encapsula toda comunicación con servicios externos (Azure Speech, OpenAI Whisper, Google Places, Google Routes, OpenRouteService, Overpass/OSM) y la persistencia de datos. Ninguna otra capa conoce los detalles de implementación de estos servicios; solo interactúan a través de las interfaces definidas en `shared/`.

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
    # Requiere: openai-whisper (incluido en pyproject.toml)
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

#### 2.1.5 NER (`spacy_ner_service.py`, `ner_factory.py`) - Proveedor NER desacoplado

**Objetivo:** extracción de localizaciones (LOC/GPE/FAC) configurable por entorno, sin acoplar Business/Application a spaCy.

**Componentes:**
- `SpacyNERService(NERServiceInterface)` en `integration/external_apis/spacy_ner_service.py`
- `NERServiceFactory` (registry pattern) en `integration/external_apis/ner_factory.py`

**Contrato principal:**
```python
class NERServiceInterface(ABC):
    async def extract_locations(self, text: str, language: str | None = None) -> Dict[str, Any]
    def is_service_available(self) -> bool
    def get_supported_languages(self) -> list[str]
    def get_service_info(self) -> Dict[str, Any]
```

**Configuración runtime (env):**
- `VOICEFLOW_NER_ENABLED=true`
- `VOICEFLOW_NER_PROVIDER=spacy`
- `VOICEFLOW_NER_DEFAULT_LANGUAGE=es`
- `VOICEFLOW_NER_MODEL_MAP={"es":"es_core_news_md","en":"en_core_web_sm"}`
- `VOICEFLOW_NER_FALLBACK_MODEL=es_core_news_sm`

**Comportamiento esperado:**
- Carga lazy por idioma/modelo y caché interna de pipelines.
- Degradación graceful cuando el modelo/proveedor no está disponible.
- Salida canónica: `locations`, `top_location`, `provider`, `model`, `language`, `status`.

#### 2.1.6 Fase 1: API Clients — Stack API-First

Todos usan `httpx.AsyncClient` y `ResilienceManager` para control de fallos.

**`google_places_client.py`** — `GooglePlacesService(PlacesServiceInterface)`

| Aspecto | Detalle |
|---------|---------|
| API | Google Places API (New) v1 |
| Endpoints | `places.googleapis.com/v1/places:searchText`, `places.googleapis.com/v1/places/{id}` |
| fieldMask | `displayName`, `formattedAddress`, `location`, `rating`, `types`, `accessibilityOptions` |
| Requiere | `VOICEFLOW_GOOGLE_API_KEY` |

**`google_directions_client.py`** — `GoogleDirectionsService(DirectionsServiceInterface)`

| Aspecto | Detalle |
|---------|---------|
| API | Google Routes API v2 |
| Endpoint | `routes.googleapis.com/directions/v2:computeRoutes` |
| Modes | TRANSIT, WALK, DRIVE, BICYCLE + wheelchair preferences |
| Requiere | `VOICEFLOW_GOOGLE_API_KEY` |

**`openroute_client.py`** — `OpenRouteDirectionsService(DirectionsServiceInterface)`

| Aspecto | Detalle |
|---------|---------|
| API | OpenRouteService v2 |
| Endpoint | `api.openrouteservice.org/v2/directions/{profile}/json` |
| Profiles | foot-walking, wheelchair, cycling-regular, driving-car |
| Requiere | `VOICEFLOW_OPENROUTE_API_KEY` (free tier) |

**`overpass_client.py`** — `OverpassAccessibilityService(AccessibilityServiceInterface)`

| Aspecto | Detalle |
|---------|---------|
| API | Overpass API (OSM) |
| Endpoint | `overpass-api.de/api/interpreter` (POST, Overpass QL) |
| Query | wheelchair-tagged nodes within 200m radius |
| Requiere | Nada (público, sin key) |

#### 2.1.7 Fase 1: Servicios locales (fallback)

Implementan las mismas interfaces que los clientes reales, envolviendo los datos mock existentes:

| Servicio | Interfaz | Fuente de datos |
|----------|----------|-----------------|
| `LocalPlacesService` | `PlacesServiceInterface` | `VENUE_DB` de `business/domains/tourism/data/venue_data.py` |
| `LocalDirectionsService` | `DirectionsServiceInterface` | `ROUTE_DB` de `business/domains/tourism/data/route_data.py` |
| `LocalAccessibilityService` | `AccessibilityServiceInterface` | `ACCESSIBILITY_DB` de `business/domains/tourism/data/accessibility_data.py` |

Siempre disponibles (`is_service_available() = True`). Usados cuando `VOICEFLOW_*_PROVIDER=local` (default).

#### 2.1.8 Fase 1: Factories

Siguen el patrón exacto de `STTServiceFactory` / `NERServiceFactory` (registry + `create_from_settings()` + fallback automático):

| Factory | Registry | Default |
|---------|----------|---------|
| `PlacesServiceFactory` | `{"google": GooglePlacesService, "local": LocalPlacesService}` | `local` |
| `DirectionsServiceFactory` | `{"google": GoogleDirectionsService, "openroute": OpenRouteDirectionsService, "local": LocalDirectionsService}` | `local` |
| `AccessibilityServiceFactory` | `{"overpass": OverpassAccessibilityService, "local": LocalAccessibilityService}` | `local` |

Si el proveedor configurado no está disponible (`is_service_available() = False`), fallback automático a `local` con warning en logs.

#### 2.1.9 Fase 1: Capa de resiliencia (`resilience.py`)

Primitivas hand-rolled (sin dependencias externas, apropiadas para PoC):

| Componente | Descripción |
|------------|-------------|
| `CircuitBreaker` | Estados CLOSED/OPEN/HALF_OPEN por servicio, threshold configurable |
| `TokenBucketRateLimiter` | async-safe, configurable RPS |
| `BudgetTracker` | Ventana horaria con coste estimado por operación |
| `ResilienceManager` | Fachada unificada: `pre_request(service, operation)` + `record_success/failure` |

Todas las llamadas a APIs externas (Phase 1) pasan por `ResilienceManager`.

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

    # NER
    ner_enabled: bool = True
    ner_provider: str = "spacy"
    ner_default_language: str = "es"
    ner_model_map: str = '{"es":"es_core_news_md","en":"en_core_web_sm"}'
    ner_fallback_model: str = "es_core_news_sm"

    # OpenAI
    openai_api_key: Optional[str] = None

    # External API settings (Phase 1)
    google_api_key: Optional[str] = None
    google_places_cache_ttl: int = 86400
    openroute_api_key: Optional[str] = None
    tool_timeout_seconds: float = 3.0

    # Resilience (Phase 1)
    circuit_breaker_threshold: int = 5
    circuit_breaker_recovery_seconds: int = 60
    api_rate_limit_rps: int = 10
    api_budget_per_hour: float = 1.0

    # Provider selection (Phase 1) — local = fallback a datos mock
    places_provider: str = "local"
    directions_provider: str = "local"
    accessibility_provider: str = "local"

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
| `VOICEFLOW_GOOGLE_API_KEY` | Para Google APIs | None | API key Google (Places + Routes) |
| `VOICEFLOW_OPENROUTE_API_KEY` | Para OpenRouteService | None | API key OpenRouteService (free tier) |
| `VOICEFLOW_PLACES_PROVIDER` | No | "local" | Proveedor de búsqueda: `local` o `google` |
| `VOICEFLOW_DIRECTIONS_PROVIDER` | No | "local" | Proveedor de rutas: `local`, `google`, o `openroute` |
| `VOICEFLOW_ACCESSIBILITY_PROVIDER` | No | "local" | Proveedor de accesibilidad: `local` u `overpass` |
| `VOICEFLOW_TOOL_TIMEOUT_SECONDS` | No | 3.0 | Timeout para llamadas a APIs externas |
| `VOICEFLOW_API_BUDGET_PER_HOUR` | No | 1.0 | Presupuesto máximo por hora (USD) |
| `VOICEFLOW_API_RATE_LIMIT_RPS` | No | 10 | Requests por segundo máximos |

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
