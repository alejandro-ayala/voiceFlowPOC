# Software Design Document: Presentation Layer

**Capa**: UI, servidor y recursos estáticos (`presentation/`)
**Fecha**: 4 de Febrero de 2026
**Estado**: Implementado

---

## 1. Propósito

La capa `presentation/` contiene la fábrica de la aplicación FastAPI, el launcher del servidor, las plantillas HTML (Jinja2) y los recursos estáticos (CSS/JS). Es el punto de entrada del sistema y la capa más externa de la arquitectura. No contiene lógica de negocio ni de aplicación; se limita a renderizar la UI, configurar middleware y delegar requests a la capa `application/`.

## 2. Componentes

### 2.1 Backend (`presentation/`)

#### 2.1.1 `fastapi_factory.py` - Fábrica de la Aplicación

**Función principal:** `create_application() -> FastAPI`

```python
def create_application() -> FastAPI:
    # 1. Lee Settings via get_settings()
    # 2. Crea instancia FastAPI con lifespan, docs condicionales
    # 3. Configura CORS middleware
    # 4. Registra routers (health, audio, chat) bajo /api/v1
    # 5. Monta archivos estáticos (/static)
    # 6. Configura Jinja2Templates
    # 7. Define ruta raíz GET / → index.html
    # 8. Registra exception handlers globales
    # 9. Retorna app
```

**Lifespan manager:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: lee settings, llama initialize_services()
    yield
    # Shutdown: log de cierre (sin cleanup real)
```

**Exception handlers registrados:**

| Handler | Excepciones | Comportamiento |
|---------|------------|----------------|
| `voiceflow_exception_handler` | `VoiceFlowException` y subclases | Mapea a HTTP status via `EXCEPTION_STATUS_CODES`, retorna `ErrorResponse` JSON |
| `general_exception_handler` | `Exception` (catch-all) | Retorna 500 con mensaje genérico (o `str(exc)` en debug mode) |

**Configuración condicional:**

| Feature | Debug=True | Debug=False |
|---------|-----------|-------------|
| Swagger UI (`/api/docs`) | Habilitado | Deshabilitado |
| ReDoc (`/api/redoc`) | Habilitado | Deshabilitado |
| Error messages detallados | `str(exc)` | `"Internal server error"` |

**Routers registrados:**

```
/api/v1/health/*  → application.api.v1.health.router
/api/v1/audio/*   → application.api.v1.audio.router
/api/v1/chat/*    → application.api.v1.chat.router
```

**Instancia global:**

```python
app = create_application()  # Ejecutado al importar el módulo
```

**Función `main()`:**

```python
def main():
    uvicorn.run(
        "presentation.fastapi_factory:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
        log_level="info" | "debug"
    )
```

**Structured logging:** Configura `structlog` con procesadores JSON, timestamps ISO, stack info y filtrado por nivel. Se ejecuta a nivel de módulo (side effect al importar).

#### 2.1.2 `server_launcher.py` - Launcher del Servidor

**Función:** Script de conveniencia para ejecutar el servidor con setup de entorno y validación de dependencias.

```python
def main():
    # 1. Parsea argumentos CLI (--host, --port, --reload, --log-level, --check-deps)
    # 2. Llama setup_environment() → carga .env, setea defaults
    # 3. Llama check_dependencies() → verifica fastapi, uvicorn, multipart, jinja2, dotenv
    # 4. Imprime banner con info del servidor
    # 5. Importa y llama presentation.fastapi_factory.main()
```

**Argumentos CLI:**

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--host` | `$HOST` o `127.0.0.1` | Host de binding |
| `--port` | `$PORT` o `8000` | Puerto de binding |
| `--reload` | `$DEBUG == 'true'` | Auto-reload para desarrollo |
| `--log-level` | `$LOG_LEVEL` o `info` | Nivel de logging |
| `--check-deps` | `false` | Solo verificar dependencias y salir |

**Dependencias verificadas:** `fastapi`, `uvicorn`, `python-multipart`, `jinja2`, `python-dotenv`

**Observación:** `setup_environment()` implementa un parser `.env` manual en vez de usar `python-dotenv` (que ya es dependencia verificada). Además, `sys.path.insert` apunta a `Path(__file__).parent` (presentation/) en vez de la raíz del proyecto, aunque esto no causa problema porque `run-ui.py` ya configura el path correctamente.

### 2.2 Frontend (`presentation/templates/`, `presentation/static/`)

#### 2.2.1 `templates/index.html` - Plantilla Principal

**Motor:** Jinja2
**Framework CSS:** Bootstrap 5.3.0 (CDN)
**Iconos:** Bootstrap Icons 1.11.0 (CDN)

**Variables de contexto Jinja2:**

| Variable | Origen | Uso |
|----------|--------|-----|
| `title` | `settings.app_name` | Tag `<title>` |
| `environment` | Implícito | Badge en navbar |
| `debug` | `settings.debug` | Renderizado condicional del Debug Panel |

**Observación:** La plantilla referencia `{{ title }}` y `{{ environment }}`, pero `create_application()` pasa `app_name`, `app_description`, `version`, `debug` al contexto del template. La variable `title` no se pasa explícitamente (posible bug: se renderizaría vacío), y `environment` tampoco se pasa.

**Estructura de la UI:**

```
body
├── navbar (VoiceFlow PoC, environment badge)
├── container
│   ├── Status Bar (system-status, backend-status, audio-status)
│   ├── row
│   │   ├── col-md-6: Audio Recording Panel
│   │   │   ├── Record Button (#recordBtn)
│   │   │   ├── Audio Visualizer (canvas #visualizerCanvas)
│   │   │   ├── File Upload (#audioFile)
│   │   │   ├── Language Select (#languageSelect: es-ES, en-US, fr-FR, de-DE)
│   │   │   └── Transcription Result (#transcriptionResult)
│   │   └── col-md-6: Chat Interface
│   │       ├── Chat Messages (#chatMessages, 400px scroll)
│   │       └── Input Group (text input + send + process audio)
│   └── Debug Panel (condicional {% if debug %})
├── Loading Modal (#loadingModal, static backdrop)
└── Error Modal (#errorModal, con detalles colapsables)
```

**Scripts cargados (orden):**

1. Bootstrap 5.3.0 bundle (CDN)
2. `/static/js/audio.js` → define `AudioHandler`
3. `/static/js/chat.js` → define `ChatHandler`
4. `/static/js/app.js` → define `VoiceFlowApp`
5. Inline: `DOMContentLoaded → VoiceFlowApp.init()`

#### 2.2.2 `templates/404.html` y `templates/500.html` - Páginas de Error

Plantillas estáticas para errores HTTP. No se referencian desde `fastapi_factory.py` (FastAPI usa sus handlers JSON por defecto).

**Observación:** Estas plantillas no están conectadas a ningún handler. Para que funcionen, se necesitaría registrar handlers adicionales en la fábrica.

#### 2.2.3 `static/js/app.js` - Coordinador Principal

**Objeto global:** `window.VoiceFlowApp`

```javascript
VoiceFlowApp = {
    audioHandler: null,      // Instancia de AudioHandler
    chatHandler: null,       // Instancia de ChatHandler
    isInitialized: false,

    async init()                    // Inicializa componentes y event handlers
    async initializeComponents()    // Crea AudioHandler y ChatHandler
    setupGlobalEventHandlers()      // online/offline, error, unhandledrejection
    showWelcomeMessage()            // Muestra mensaje en #transcriptionResult
    showError(msg)                  // Modal de error Bootstrap
    showSuccess(msg)                // Notificación de éxito
    showWarning(msg)                // Notificación de advertencia
}
```

**Patrón:** Mediator — coordina `AudioHandler` y `ChatHandler` sin que se conozcan entre sí.

#### 2.2.4 `static/js/audio.js` - Manejo de Audio

**Clase:** `AudioHandler`

```javascript
class AudioHandler {
    // Estado
    mediaRecorder: MediaRecorder
    audioChunks: []
    isRecording: boolean
    audioContext: AudioContext
    analyser: AnalyserNode
    stream: MediaStream

    // Métodos principales
    async init()                    // Configura elementos DOM y event listeners
    initVisualizer()                // Canvas para visualización de ondas
    async toggleRecording()         // Start/stop grabación
    async startRecording()          // getUserMedia() + MediaRecorder
    async stopRecording()           // Detiene y envía a /api/v1/audio/transcribe
    async handleFileUpload(event)   // Envía archivo a /api/v1/audio/transcribe
    async sendAudioForTranscription(blob, filename)  // POST multipart/form-data
    updateVisualization()           // requestAnimationFrame loop con AnalyserNode
}
```

**API calls:**

| Acción | Endpoint | Método | Content-Type |
|--------|----------|--------|--------------|
| Transcribir | `/api/v1/audio/transcribe` | POST | `multipart/form-data` |

**Audio capturado:** Format WebM (default de `MediaRecorder` en navegadores). Se envía como `audio_file` en FormData con el idioma seleccionado.

#### 2.2.5 `static/js/chat.js` - Manejo de Chat

**Clase:** `ChatHandler`

```javascript
class ChatHandler {
    // Estado
    conversationId: string    // 'conv_' + timestamp + random
    messages: []
    isProcessing: boolean

    // Métodos principales
    init()                           // Configura DOM y genera conversation ID
    generateConversationId()         // ID único basado en timestamp
    async sendMessage(text?)         // POST /api/v1/chat/message
    async processAudioTranscription()  // Toma texto de #transcriptionResult y llama sendMessage()
    addMessageToUI(text, type)       // Renderiza mensaje en #chatMessages
    clearChat()                      // Limpia mensajes y genera nuevo conversation ID
    showError(msg)                   // Muestra error en el chat
}
```

**API calls:**

| Acción | Endpoint | Método | Body |
|--------|----------|--------|------|
| Enviar mensaje | `/api/v1/chat/message` | POST | `{ message, conversation_id }` |

#### 2.2.6 `static/css/app.css` - Estilos Personalizados

**Estructura:**

| Sección | Descripción |
|---------|-------------|
| CSS Variables | `--primary-color` a `--dark-color` (Bootstrap-compatible) |
| General | Font family, background, card shadows |
| Card Headers | Gradient azul (`var(--primary-color)` a `#0b5ed7`) |
| Record Button | Transiciones, hover scale, animación `pulse-red` para grabación activa |
| Audio Visualizer | Background gradient, border-radius |
| Chat Messages | Background blanco, border, padding, animación `slideIn` |

## 3. Diagrama de dependencias

```
presentation/fastapi_factory.py
    → integration/configuration/settings (get_settings, get_cors_config)
    → shared/exceptions/exceptions (VoiceFlowException, EXCEPTION_STATUS_CODES)
    → shared/utils/dependencies (initialize_services)
    → application/api/v1 (health, audio, chat routers)
    → application/models/responses (ErrorResponse, StatusEnum)
    → structlog, uvicorn, fastapi (externos)

presentation/server_launcher.py
    → presentation/fastapi_factory (main)
    → os, sys, argparse, pathlib (stdlib)

presentation/templates/index.html
    → /static/js/audio.js (AudioHandler)
    → /static/js/chat.js (ChatHandler)
    → /static/js/app.js (VoiceFlowApp)
    → Bootstrap 5.3.0 CDN
    → Bootstrap Icons 1.11.0 CDN

static/js/app.js
    → AudioHandler (desde audio.js)
    → ChatHandler (desde chat.js)
    → DOM API, Bootstrap Modal API

static/js/audio.js
    → MediaRecorder API, AudioContext API
    → fetch() → /api/v1/audio/transcribe

static/js/chat.js
    → fetch() → /api/v1/chat/message
    → DOM API
```

## 4. Flujo de arranque

```
run-ui.py / server_launcher.py
    → presentation.fastapi_factory.main()
        → uvicorn.run("presentation.fastapi_factory:app", ...)
            → Importa módulo → ejecuta create_application()
                → get_settings()
                → FastAPI(lifespan=lifespan, ...)
                → CORSMiddleware(**get_cors_config())
                → include_router(health, audio, chat)
                → mount("/static", StaticFiles)
                → Jinja2Templates(templates/)
                → exception handlers
            → lifespan startup:
                → initialize_services()
            → Servidor listo en http://host:port
```

## 5. Flujo de interacción usuario

```
Browser → GET / → fastapi_factory → Jinja2 → index.html
    → Carga audio.js, chat.js, app.js
    → DOMContentLoaded → VoiceFlowApp.init()
        → new AudioHandler() → configura micrófono, canvas
        → new ChatHandler() → genera conversation ID

User clicks Record:
    → AudioHandler.toggleRecording()
    → getUserMedia() → MediaRecorder.start()
    → updateVisualization() loop (canvas)

User clicks Stop:
    → MediaRecorder.stop() → Blob(webm)
    → POST /api/v1/audio/transcribe (FormData)
    → Respuesta → #transcriptionResult actualizado
    → #processAudioBtn habilitado

User clicks "Procesar Audio":
    → ChatHandler.processAudioTranscription()
    → Lee texto de #transcriptionResult
    → POST /api/v1/chat/message { message, conversation_id }
    → Respuesta → addMessageToUI(user + ai)

User escribe texto + Send:
    → ChatHandler.sendMessage()
    → POST /api/v1/chat/message
    → Respuesta → addMessageToUI()
```

## 6. Patrones de diseño

| Patrón | Componente | Descripción |
|--------|-----------|-------------|
| Factory | `create_application()` | Crea y configura instancia FastAPI con todas sus dependencias |
| Mediator | `VoiceFlowApp` (app.js) | Coordina AudioHandler y ChatHandler sin acoplamiento directo |
| Observer | Event listeners (JS) | DOM events, online/offline, MediaRecorder events |
| Template Method | `index.html` (Jinja2) | Template base con variables de contexto y renderizado condicional |
| Module Pattern | `VoiceFlowApp` global | Namespace global para evitar colisiones, encapsula estado |

## 7. Estrategia de testing

```python
# Test fábrica: verificar que create_application() retorna FastAPI configurada
def test_create_application_returns_fastapi():
    from presentation.fastapi_factory import create_application
    app = create_application()
    assert isinstance(app, FastAPI)
    assert len(app.routes) > 0

# Test routers registrados
def test_api_routes_registered():
    from presentation.fastapi_factory import app
    paths = [route.path for route in app.routes]
    assert "/api/v1/health/" in paths
    assert "/api/v1/audio/transcribe" in paths
    assert "/api/v1/chat/message" in paths

# Test exception handler
def test_voiceflow_exception_returns_correct_status(test_client):
    # Provocar AudioProcessingException → esperar 422
    # Provocar ValidationException → esperar 400

# Test página principal
def test_root_returns_html(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "VoiceFlow" in response.text

# Test static files
def test_static_css_accessible(test_client):
    response = test_client.get("/static/css/app.css")
    assert response.status_code == 200

# Test docs condicionales
def test_docs_disabled_in_production():
    # Con debug=False, /api/docs debe retornar 404
```

## 8. Deuda técnica identificada

1. **Variables de contexto Jinja2 incorrectas:** `index.html` usa `{{ title }}` y `{{ environment }}`, pero la ruta `GET /` pasa `app_name`, `app_description`, `version`, `debug`. Las variables `title` y `environment` se renderizarían vacías.
2. **Templates 404/500 no conectados:** `404.html` y `500.html` existen pero no hay handlers que los sirvan; FastAPI retorna JSON por defecto en errores.
3. **Logging configurado como side effect:** `structlog.configure()` y `logging.basicConfig()` se ejecutan al importar `fastapi_factory.py`, lo que dificulta testing y reconfigurabilidad.
4. **`server_launcher.py` duplica funcionalidad de `run-ui.py`:** Ambos scripts hacen esencialmente lo mismo. `server_launcher.py` añade validación de dependencias y parsing `.env` manual (ya soportado por Pydantic `BaseSettings`).
5. **`sys.path.insert` en `server_launcher.py`:** Apunta a `presentation/` en vez de la raíz del proyecto. Funciona por casualidad porque `run-ui.py` ya configura el path.
6. **CDN sin fallback:** Bootstrap CSS/JS se cargan desde CDN sin fallback local. Si el CDN falla, la UI se rompe completamente.
7. **`initialize_services()` crea instancias duplicadas:** Como se documenta en el SDD de shared/, las instancias globales creadas en startup no se usan (el DI por request crea las suyas).
8. **Sin CSP ni headers de seguridad:** No se configura Content-Security-Policy, X-Frame-Options, ni otros headers de seguridad HTTP.
9. **`conversation_id` generado en frontend:** El ID se genera con `Date.now() + Math.random()`, lo cual no es criptográficamente seguro ni globalmente único. Debería generarse en el backend con UUID.
