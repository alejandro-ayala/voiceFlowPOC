# Software Design Document: Presentation Layer

**Capa**: UI, servidor y recursos estáticos (`presentation/`)
**Fecha**: 17 de Febrero de 2026
**Estado**: Implementado
**Última actualización**: Integración de features P0 (F1 Pipeline Visualizer, F2 Rich Cards, F6 Demo Scenarios)

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
    # 7. Define ruta raíz GET / → index.html (con demo_scenarios flag)
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

**Variables de entorno para la UI:**

| Variable | Default | Uso |
|----------|---------|-----|
| `DEMO_SCENARIOS` | `false` | Habilita la barra de demo scenarios en el frontend. Se inyecta como `window.DEMO_SCENARIOS` via Jinja2 |

**Routers registrados:**

```
/api/v1/health/*  → application.api.v1.health.router
/api/v1/audio/*   → application.api.v1.audio.router
/api/v1/chat/*    → application.api.v1.chat.router
```

Endpoints relevantes del chat router para la capa de presentación:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/chat/message` | POST | Envía mensaje y recibe respuesta con `tourism_data`, `pipeline_steps`, `intent`, `entities` |
| `/api/v1/chat/demo/scenarios` | GET | Retorna escenarios predefinidos para el modo demo |

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
| `demo_scenarios` | `os.getenv("DEMO_SCENARIOS")` | Flag inyectado como `window.DEMO_SCENARIOS` para habilitar el modo demo |

**Observación:** La plantilla referencia `{{ title }}` y `{{ environment }}`, pero `create_application()` pasa `app_name`, `app_description`, `version`, `debug` al contexto del template. La variable `title` no se pasa explícitamente (posible bug: se renderizaría vacío), y `environment` tampoco se pasa.

**Estructura de la UI:**

```
body
├── navbar (VoiceFlow PoC, environment badge, Demo toggle link)
├── container
│   ├── Status Bar (system-status, backend-status, audio-status)
│   ├── #demoBar [injected by DemoModeHandler]       ← F6
│   ├── #pipelineVisualizer [injected, hidden]       ← F1
│   ├── row (Main Interface)
│   │   ├── col-md-6: Audio Recording Panel
│   │   │   ├── Record Button (#recordBtn)
│   │   │   ├── Audio Visualizer (canvas #visualizerCanvas)
│   │   │   ├── File Upload (#audioFile)
│   │   │   ├── Language Select (#languageSelect: es-ES, en-US, fr-FR, de-DE)
│   │   │   └── Transcription Result (#transcriptionResult)
│   │   └── col-md-6: Chat Interface
│   │       ├── Chat Messages (#chatMessages, 400px scroll)
│   │       │   └── Rich Cards (venue, accessibility, routes)  ← F2
│   │       └── Input Group (text input + send + process audio)
│   └── Debug Panel (condicional {% if debug %})
├── Loading Modal (#loadingModal, static backdrop)
└── Error Modal (#errorModal, con detalles colapsables)
```

**Inline script:** Antes de los scripts estáticos, se inyecta el flag de demo scenarios:

```html
<script>
    window.DEMO_SCENARIOS = {{ demo_scenarios | tojson }};
</script>
```

**Scripts cargados (orden):**

1. Bootstrap 5.3.0 bundle (CDN)
2. Inline: `window.DEMO_SCENARIOS = {{ demo_scenarios | tojson }}`
3. `/static/js/audio.js` → define `AudioHandler`
4. `/static/js/chat.js` → define `ChatHandler`
5. `/static/js/cards.js` → define `CardRenderer` ← F2
6. `/static/js/pipeline.js` → define `PipelineVisualizer` ← F1
7. `/static/js/demo.js` → define `DemoModeHandler` ← F6
8. `/static/js/app.js` → define `VoiceFlowApp`
9. Inline: `DOMContentLoaded → VoiceFlowApp.init()`

**Orden importante:** `cards.js` se carga antes de `chat.js` lo usa (`CardRenderer`). `pipeline.js` y `demo.js` se cargan antes de que `app.js` los instancie.

#### 2.2.2 `templates/404.html` y `templates/500.html` - Páginas de Error

Plantillas estáticas para errores HTTP. No se referencian desde `fastapi_factory.py` (FastAPI usa sus handlers JSON por defecto).

**Observación:** Estas plantillas no están conectadas a ningún handler. Para que funcionen, se necesitaría registrar handlers adicionales en la fábrica.

#### 2.2.3 `static/js/app.js` - Coordinador Principal

**Objeto global:** `window.VoiceFlowApp`

```javascript
VoiceFlowApp = {
    audioHandler: null,          // Instancia de AudioHandler
    chatHandler: null,           // Instancia de ChatHandler
    pipelineVisualizer: null,    // Instancia de PipelineVisualizer       ← F1
    demoHandler: null,           // Instancia de DemoModeHandler          ← F6
    isInitialized: false,

    async init()                    // Inicializa componentes y event handlers
    async initializeComponents()    // Crea todos los handlers con fault-isolation
    setupGlobalEventHandlers()      // online/offline, error, unhandledrejection
    showWelcomeMessage()            // Muestra mensaje en #transcriptionResult
    showError(msg)                  // Alerta en #transcriptionResult (type=danger)
    showSuccess(msg)                // Alerta en #transcriptionResult (type=success)
    showWarning(msg)                // Alerta en #transcriptionResult (type=warning)
    showInfo(msg)                   // Alerta en #transcriptionResult (type=info)
    showMessage(msg, type, icon)    // Método base para alertas
    getStatus()                     // Retorna estado de inicialización
}
```

**Inicialización con fault-isolation:**

Cada componente se inicializa dentro de su propio `try-catch`, de forma que un fallo en uno no impide la inicialización de los demás:

```javascript
async initializeComponents() {
    try { this.audioHandler = new AudioHandler(); }
    catch (e) { console.error('AudioHandler init failed:', e); }

    try { this.chatHandler = new ChatHandler(); }
    catch (e) { console.error('ChatHandler init failed:', e); }

    try {
        this.pipelineVisualizer = new PipelineVisualizer();      // F1
        this.pipelineVisualizer.init();
    } catch (e) { console.error('PipelineVisualizer init failed:', e); }

    try {
        if (window.DEMO_SCENARIOS) {                             // F6
            this.demoHandler = new DemoModeHandler();
            await this.demoHandler.init();
        }
    } catch (e) { console.error('DemoModeHandler init failed:', e); }
}
```

**Globals exportados:**

```javascript
window.showError = (msg) => VoiceFlowApp.showError(msg);
window.showSuccess = (msg) => VoiceFlowApp.showSuccess(msg);
window.showWarning = (msg) => VoiceFlowApp.showWarning(msg);
window.showInfo = (msg) => VoiceFlowApp.showInfo(msg);
window.DEBUG = { app, audio, chat };
```

**Patrón:** Mediator — coordina `AudioHandler`, `ChatHandler`, `PipelineVisualizer` y `DemoModeHandler` sin que se conozcan directamente entre sí (acceden via `window.VoiceFlowApp`).

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
    init()                              // Configura DOM y genera conversation ID
    generateConversationId()            // ID único basado en timestamp
    async sendMessage(text?)            // Orquesta: pipeline animation → backend → cards
    async processAudioTranscription()   // Toma texto de #transcriptionResult y llama sendMessage()
    async sendToBackend(message)        // POST /api/v1/chat/message (separado para reuso por DemoModeHandler)
    addMessage(role, content, metadata) // Renderiza mensaje con cards si hay tourismData
    clearChat()                         // Limpia mensajes y genera nuevo conversation ID
    escapeHtml(text)                    // Escape XSS de & < > " '
    scrollToBottom()                    // Auto-scroll del chat
    setButtonsLoading(loading)          // Deshabilita/habilita botones durante procesamiento
    showError(msg)                      // Muestra error via Bootstrap Modal
}
```

**Integración con Pipeline Visualizer (F1):**

En `sendMessage()`, antes de enviar al backend:

```javascript
const pipelineViz = window.VoiceFlowApp?.pipelineVisualizer;
if (pipelineViz) pipelineViz.startAnimation(null);
```

Tras recibir respuesta, actualiza con timings reales del servidor:

```javascript
if (pipelineViz && response.pipeline_steps) {
    pipelineViz.completeFromResponse(response);
}
```

**Integración con Rich Cards (F2):**

En `addMessage()`, si la respuesta incluye `tourismData`:

```javascript
if (role === 'assistant' && metadata.tourismData && typeof CardRenderer !== 'undefined') {
    messageHtml += CardRenderer.render(metadata.tourismData);
    messageElement.classList.add('has-cards');  // Expande max-width a 95%
}
```

**Metadata en mensajes:** Cada mensaje assistant incluye un footer `.message-meta` con timestamp y tiempo de procesamiento.

**API calls:**

| Acción | Endpoint | Método | Body |
|--------|----------|--------|------|
| Enviar mensaje | `/api/v1/chat/message` | POST | `{ message, conversation_id, context }` |

**Globals exportados:**

```javascript
window.handleMessageKeyPress  // Enter sin Shift → sendMessage()
window.sendMessage             // Wrapper global
window.processTranscription    // Wrapper global
window.ChatHandler             // Clase exportada
```

#### 2.2.6 `static/js/cards.js` - Rich Response Cards (F2)

**Clase:** `CardRenderer` (todos los métodos son `static` — no requiere instanciación)

```javascript
class CardRenderer {
    static FACILITY_ICONS = { ... }    // 8 facility keys → { icon, label }
    static TRANSPORT_ICONS = { ... }   // 4 transport types → icon class

    static render(tourismData)                  // Entry point: genera todas las cards aplicables
    static renderVenueCard(venue)               // Nombre, gauge circular, facilities, horarios, precios
    static renderAccessibilityCard(accessibility) // Score bar, level, certification, services
    static renderRouteCards(routes)             // 1 card por ruta: icono transporte, pasos, coste
    static escapeHtml(text)                     // Prevención XSS
}
```

**Facility icon mapping:**

| Key | Icono Bootstrap | Label |
|-----|----------------|-------|
| `wheelchair_ramps` | `bi-person-wheelchair` | Rampas |
| `adapted_bathrooms` | `bi-droplet` | Aseos adaptados |
| `audio_guides` | `bi-headphones` | Audioguias |
| `tactile_paths` | `bi-hand-index` | Rutas tactiles |
| `sign_language_interpreters` | `bi-hand-thumbs-up` | Lengua de signos |
| `elevator_access` | `bi-arrow-up-square` | Ascensor |
| `wheelchair_spaces` | `bi-person-wheelchair` | Espacios reservados |
| `hearing_loops` | `bi-ear` | Bucle auditivo |

Keys no reconocidos se renderizan con icono genérico `bi-check-circle` y label derivado del key (underscores → espacios).

**Transport icon mapping:**

| Transport | Icono Bootstrap |
|-----------|----------------|
| `metro` | `bi-train-front` |
| `bus` | `bi-bus-front` |
| `taxi` | `bi-taxi-front` |
| `walking` | `bi-person-walking` |

Transporte no reconocido usa fallback `bi-signpost-2`.

**Score color thresholds:**

| Score | Color | CSS class |
|-------|-------|-----------|
| >= 8 | Verde (success) | `gauge-success`, `bg-success` |
| >= 6 | Amarillo (warning) | `gauge-warning`, `bg-warning` |
| < 6 | Rojo (danger) | `gauge-danger`, `bg-danger` |

**Venue card structure:**

```
┌─────────────────────────────────────────────┐
│ 🏛 Museo del Prado              ┌──────┐   │
│ 🏆 ONCE certified               │ 9.2  │   │
│                                  │ /10  │   │
│ [Rampas] [Aseos] [Audioguias]   └──────┘   │
│ 🕐 monday saturday: 10-20                   │
│ 🏷 general: 15€ | reduced: 7.50€            │
└─────────────────────────────────────────────┘
```

**Data contract:** El objeto `tourism_data` que consume `CardRenderer` se documenta en detalle en `documentation/SDD/User_Profile_Preferennces.md` (SPECS Rich Cards).

#### 2.2.7 `static/js/pipeline.js` - Pipeline Visualizer (F1)

**Clase:** `PipelineVisualizer`

```javascript
class PipelineVisualizer {
    // Estado
    steps: [                            // 5 pasos fijos del pipeline
        { name: 'NLU', icon: 'bi-brain', tool: 'tourism_nlu' },
        { name: 'Accessibility', icon: 'bi-universal-access', tool: 'accessibility_analysis' },
        { name: 'Routes', icon: 'bi-map', tool: 'route_planning' },
        { name: 'Venue Info', icon: 'bi-info-circle', tool: 'tourism_info' },
        { name: 'Response', icon: 'bi-chat-square-text', tool: 'llm_synthesis' },
    ]
    container: HTMLElement | null
    currentStep: number               // -1 = no step active
    _animationResolve: Function       // Promise resolve for animation coordination

    // Métodos principales
    init()                                   // Llama buildUI()
    buildUI()                                // Crea DOM, inyecta en container (hidden)
    reset()                                  // Todos los steps a idle, limpia timings
    async startAnimation(pipelineSteps?)     // Animación secuencial con timings
    completeFromResponse(response)           // Completa instantáneamente desde datos del servidor
}
```

**Step states:**

| State | CSS class | Visual |
|-------|-----------|--------|
| `idle` | `.pipeline-step.idle` | Icono dimmed, colores muted |
| `processing` | `.pipeline-step.processing` | Borde cyan, pulse animation, glow |
| `completed` | `.pipeline-step.completed` | Icono verde, checkmark, muestra duración |

**Animation timing (defaults):** `[450, 620, 880, 540, 710]` ms — total ~3.2s. Si se pasan `pipelineSteps` con `duration_ms`, se usan esos timings.

**DOM injection:** El container se crea como `<div class="row mb-4 d-none">` e inyecta antes del main interface row. Se revela quitando `d-none` en `startAnimation()`.

**Coordinación con DemoModeHandler:** `completeFromResponse()` resuelve cualquier Promise pendiente de `startAnimation()`, permitiendo sincronizar animación con datos reales del servidor.

#### 2.2.8 `static/js/demo.js` - Demo Mode Handler (F6)

**Clase:** `DemoModeHandler`

```javascript
class DemoModeHandler {
    // Estado
    scenarios: []                  // Array de objetos scenario
    isRunning: boolean             // Previene ejecución concurrente
    currentScenario: object | null
    container: HTMLElement | null

    // Métodos principales
    async init()                          // loadScenarios → buildDemoBar → setupNavbarToggle
    async loadScenarios()                 // GET /api/v1/chat/demo/scenarios (con fallback)
    getFallbackScenarios()                // 4 escenarios hardcoded
    buildDemoBar()                        // Crea card con botones, toggle Real API, collapse
    setupNavbarToggle()                   // Añade link "Demo" en navbar
    toggleDemoBar()                       // Toggle d-none en contenedor de botones
    async runScenario(index)              // Orquestación completa: clear → typewriter → pipeline → cards
    async typewriterEffect(text)          // Animación palabra por palabra (60ms/word)
}
```

**Escenarios predefinidos (fallback):**

| ID | Título | Icono | Query |
|----|--------|-------|-------|
| `prado_wheelchair` | Museo del Prado accesible | `bi-building` | "Quiero visitar el Museo del Prado en silla de ruedas" |
| `reina_sofia_transport` | Transporte al Reina Sofía | `bi-map` | "¿Cómo llego al Museo Reina Sofía en transporte accesible?" |
| `restaurants_centro` | Restaurantes accesibles | `bi-cup-hot` | "Recomiéndame restaurantes accesibles en el centro" |
| `concert_hearing` | Conciertos accesibles | `bi-music-note-beamed` | "Quiero ir a un concierto, necesito acceso auditivo" |

**UI structure:**

```
┌──────────────────────────────────────────────────────────────┐
│  ▶ Demo Scenarios                      [Real API toggle] [▲] │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────┐ ┌────────┐ │
│  │ Museo Prado  │ │ Reina Sofia   │ │ Restaur. │ │ Concier│ │
│  └──────────────┘ └───────────────┘ └──────────┘ └────────┘ │
└──────────────────────────────────────────────────────────────┘
```

**Condición de activación:** Solo se instancia si `window.DEMO_SCENARIOS === true` (inyectado desde `fastapi_factory.py` via variable de entorno `DEMO_SCENARIOS`).

**Real API toggle:** Switch que controla si `runScenario()` usa el backend en modo simulación o envía a los agentes reales de LangChain:

- **Off (default):** Simulación. Pipeline animation corre en paralelo con `sendToBackend()`. Timings se actualizan desde la respuesta.
- **On:** Agentes reales. Pipeline animation arranca, luego se completa con `completeFromResponse()` cuando llega la respuesta real.

**Error recovery:** `runScenario()` tiene `try/catch/finally` que siempre rehabilita los botones, incluso si el escenario falla.

#### 2.2.9 `static/css/app.css` - Estilos Personalizados

**Estructura (719 líneas):**

| Sección | Líneas | Descripción |
|---------|--------|-------------|
| CSS Variables | 1-12 | `--primary-color` a `--dark-color` (Bootstrap-compatible) |
| General | 14-31 | Font family, background, card shadows, card headers gradient |
| Record Button | 33-62 | Transiciones, hover scale, animación `pulse-red` para grabación activa |
| Audio Visualizer | 64-76 | Background gradient, border-radius |
| Chat Messages | 78-137 | Background blanco, border, padding, animación `slideIn`, estilos por rol (user/assistant/system) |
| Status Badges | 139-143 | Font size, padding |
| Processing States | 145-168 | Overlay spinner, animación `spin` |
| Transcription Display | 170-179 | Left border indicator, `.has-content` state |
| Input Group | 181-189 | Focus states |
| Responsive (base) | 191-214 | Mobile overrides para container, botones, chat messages |
| Loading/Error States | 216-260 | Button loading spinner, error/success borders |
| Debug Panel | 248-260 | Dark theme para panel de debug |
| Transitions | 262-265 | Global smooth transitions |
| Custom Scrollbar | 267-284 | Webkit scrollbar styling para chat |
| Accessibility | 286-313 | Focus outlines, high contrast mode, reduced motion support |
| **F6 — Demo Mode** | 317-388 | `.demo-scenarios-card` (dashed border), `.demo-scenario-btn` (pill-shaped), `.active` (pulse-blue), typewriter cursor/word animations |
| **F1 — Pipeline Visualizer** | 391-492 | `.pipeline-container` (dark gradient), `.pipeline-step` states (idle/processing/completed), `.pipeline-connector` con fill animado, `pipeline-pulse` animation |
| **F2 — Rich Response Cards** | 495-683 | `.response-card` con slide-in animation, `.venue-card`/`.accessibility-card`/`.route-card` (left-border colors), `.gauge-circle` (56px circular score), `.facility-badge`, `.score-bar`, `.route-step` (numbered steps), `.message-meta`, `.has-cards` (95% width) |
| **Responsive (features)** | 686-719 | Mobile overrides para pipeline steps, demo buttons, gauge circles |

**Animaciones definidas:**

| Animation | Feature | Uso |
|-----------|---------|-----|
| `pulse-red` | Base | Botón de grabación activo |
| `slideIn` | Base | Entrada de mensajes de chat |
| `spin` | Base | Spinner de procesamiento |
| `pulse-blue` | F6 | Botón de demo scenario activo |
| `fadeInWord` | F6 | Efecto typewriter palabra por palabra |
| `blink` | F6 | Cursor parpadeante durante typewriter |
| `pipeline-pulse` | F1 | Step en estado processing |
| `cardSlideIn` | F2 | Entrada de rich cards |

## 3. Diagrama de dependencias

```
presentation/fastapi_factory.py
    → integration/configuration/settings (get_settings, get_cors_config)
    → shared/exceptions/exceptions (VoiceFlowException, EXCEPTION_STATUS_CODES)
    → shared/utils/dependencies (initialize_services)
    → application/api/v1 (health, audio, chat routers)
    → application/models/responses (ErrorResponse, StatusEnum)
    → os (DEMO_SCENARIOS env var)
    → structlog, uvicorn, fastapi (externos)

presentation/server_launcher.py
    → presentation/fastapi_factory (main)
    → os, sys, argparse, pathlib (stdlib)

presentation/templates/index.html
    → /static/js/audio.js (AudioHandler)
    → /static/js/chat.js (ChatHandler)
    → /static/js/cards.js (CardRenderer)          ← F2
    → /static/js/pipeline.js (PipelineVisualizer)  ← F1
    → /static/js/demo.js (DemoModeHandler)         ← F6
    → /static/js/app.js (VoiceFlowApp)
    → Bootstrap 5.3.0 CDN
    → Bootstrap Icons 1.11.0 CDN

static/js/app.js
    → AudioHandler (desde audio.js)
    → ChatHandler (desde chat.js)
    → PipelineVisualizer (desde pipeline.js)       ← F1
    → DemoModeHandler (desde demo.js)              ← F6
    → window.DEMO_SCENARIOS (desde index.html inline script)
    → DOM API, Bootstrap Modal API

static/js/audio.js
    → MediaRecorder API, AudioContext API
    → fetch() → /api/v1/audio/transcribe

static/js/chat.js
    → CardRenderer (desde cards.js)                ← F2
    → window.VoiceFlowApp.pipelineVisualizer       ← F1
    → fetch() → /api/v1/chat/message
    → DOM API

static/js/cards.js                                 ← F2
    → (sin dependencias externas, solo DOM API)

static/js/pipeline.js                              ← F1
    → DOM API

static/js/demo.js                                  ← F6
    → window.VoiceFlowApp.chatHandler
    → window.VoiceFlowApp.pipelineVisualizer       ← F1
    → fetch() → /api/v1/chat/demo/scenarios
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
                → Lee DEMO_SCENARIOS env var
                → exception handlers
            → lifespan startup:
                → initialize_services()
            → Servidor listo en http://host:port
```

**Frontend initialization:**

```
DOMContentLoaded
  └→ VoiceFlowApp.init()
       └→ initializeComponents()
            ├→ new AudioHandler()              [try-catch aislado]
            ├→ new ChatHandler()               [try-catch aislado]
            ├→ new PipelineVisualizer()         [try-catch aislado]  ← F1
            │    └→ .init() → buildUI() → inserts into DOM (hidden)
            └→ if (DEMO_SCENARIOS):
                 new DemoModeHandler()          [try-catch aislado]  ← F6
                   └→ await .init()
                        ├→ loadScenarios()      fetch /api/v1/chat/demo/scenarios
                        ├→ buildDemoBar()       inserts into DOM (visible)
                        └→ setupNavbarToggle()
```

## 5. Flujos de interacción usuario

### 5.1 Flujo base: Audio → Chat

```
Browser → GET / → fastapi_factory → Jinja2 → index.html
    → Carga audio.js, chat.js, cards.js, pipeline.js, demo.js, app.js
    → DOMContentLoaded → VoiceFlowApp.init()
        → new AudioHandler() → configura micrófono, canvas
        → new ChatHandler() → genera conversation ID
        → new PipelineVisualizer() → buildUI() (hidden)
        → new DemoModeHandler() → loadScenarios() + buildDemoBar()

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
    → ChatHandler.sendMessage(texto)
```

### 5.2 Flujo chat: Texto/Audio → Pipeline → Cards

```
User escribe texto + Send (o processAudioTranscription):
    → ChatHandler.sendMessage()
    → addMessage('user', message)
    → PipelineVisualizer.startAnimation(null)        ← F1: pipeline se anima
    → POST /api/v1/chat/message { message, conversation_id }
    → Respuesta con { ai_response, tourism_data, pipeline_steps, intent, entities }
    → PipelineVisualizer.completeFromResponse(response)  ← F1: timings reales
    → addMessage('assistant', response, { tourismData, pipelineSteps })
        → CardRenderer.render(tourismData)               ← F2: rich cards
        → .message-meta con timestamp + processing time
```

### 5.3 Flujo demo: Scenario → Pipeline → Cards

```
User clicks demo scenario button:                        ← F6
    → DemoModeHandler.runScenario(index)
    → chatHandler.clearChat() + pipelineViz.reset()
    → typewriterEffect(query)    word-by-word en transcription box (~1.5s)
    → addMessage('user', query)
    │
    ├── [Real API OFF — simulación]:
    │   → Promise.all([sendToBackend(), startAnimation()])
    │   → completeFromResponse() con datos del servidor
    │
    └── [Real API ON — agentes reales]:
        → startAnimation(null)   animación con timings default
        → sendToBackend()        espera respuesta real
        → completeFromResponse() snap a timings reales
    │
    → addMessage('assistant', response, { tourismData })
        → CardRenderer.render()  venue + accessibility + route cards
```

## 6. DOM Injection Strategy

`DemoModeHandler` y `PipelineVisualizer` se inyectan dinámicamente en el DOM. El punto de inserción es el main content area, entre la status bar y la interfaz principal.

**Selector chain:**

```javascript
// 1. Find the main content container (skip the <nav>'s .container)
const mainContainer = document.querySelector('.container-fluid > .container');

// 2. Find the first direct-child .row without .mb-4 (= main interface)
const mainInterface = mainContainer.querySelector(':scope > .row:not(.mb-4)');

// 3. Insert before it
mainContainer.insertBefore(element, mainInterface);
```

**Por qué `:scope >`:** El HTML contiene `.row` anidados dentro de Bootstrap cards (e.g., `<div class="row align-items-center">` dentro de la status bar). Sin `:scope >`, `querySelector` matchea el primer `.row:not(.mb-4)` en todo el subárbol — que es el anidado, no el row principal.

**DOM resultante:**

```
.container-fluid
  └ nav.navbar
      └ .container          ← skipped (not direct child of .container-fluid)
  └ .container              ← mainContainer
      ├ .row.mb-4           ← Status bar
      ├ #demoBar.row.mb-4   ← Demo bar (injected by DemoModeHandler)     ← F6
      ├ #pipelineVisualizer.row.mb-4.d-none  ← Pipeline (injected, hidden) ← F1
      ├ .row                ← Main interface (mainInterface reference)
      └ .row.mt-4           ← Debug panel (if debug mode)
```

## 7. Data Contracts

### 7.1 `tourism_data` Object Shape

Consumido por `CardRenderer.render()`. Documentación completa del schema en `documentation/SDD/User_Profile_Preferennces.md`.

```typescript
interface TourismData {
  venue?: {
    name: string;
    type: string;                           // "museum" | "entertainment" | "restaurant" | "park"
    accessibility_score: number;            // 0-10
    certification?: string;                 // e.g. "ONCE_certified"
    facilities: string[];                   // keys from FACILITY_ICONS
    opening_hours?: Record<string, string>;
    pricing?: Record<string, string>;
  };
  routes?: Array<{
    transport: string;          // "metro" | "bus" | "taxi" | "walking"
    line?: string;              // e.g. "Metro Line 2"
    duration: string;           // e.g. "25 min"
    accessibility: string;      // "full" | "partial"
    cost: string;               // e.g. "2.50€"
    steps: string[];            // ordered directions
  }>;
  accessibility?: {
    level: string;              // e.g. "full_wheelchair_access"
    score: number;              // 0-10
    certification?: string;
    facilities: string[];
    services?: Record<string, string>;
  };
}
```

### 7.2 `pipeline_steps` Array Shape

Consumido por `PipelineVisualizer.completeFromResponse()`.

```typescript
interface PipelineStep {
  name: string;         // Display name (e.g. "NLU", "Accessibility")
  tool: string;         // Tool identifier (e.g. "tourism_nlu", "llm_synthesis")
  status: string;       // "pending" | "processing" | "completed" | "error"
  duration_ms: number;  // Milliseconds
  summary: string;      // Brief description of step output
}
```

## 8. Error Handling

### Frontend

- **Component isolation:** Cada componente en `app.js` está wrapeado en su propio `try-catch`. Un fallo en `PipelineVisualizer` no impide que `DemoModeHandler` cargue (y viceversa).
- **DOM null-safety:** `pipeline.js` y `demo.js` comprueban null antes de operaciones DOM y retornan early con console warning.
- **Scenario fallback:** `DemoModeHandler.loadScenarios()` captura errores de fetch y usa escenarios hardcoded.
- **Demo error recovery:** `runScenario()` tiene `try/catch/finally` que siempre rehabilita botones, incluso si el escenario falla.
- **CardRenderer availability check:** `chat.js` comprueba `typeof CardRenderer !== 'undefined'` antes de invocar rendering.

### Backend

- **Graceful degradation:** `_get_simulation_metadata()` retorna `tourism_data: None` para queries no reconocidas. El frontend no renderiza cards en este caso.
- **Field optionality:** Todos los campos nuevos de `ChatResponse` (`tourism_data`, `pipeline_steps`, `intent`, `entities`) son `Optional` con `default=None`.

## 9. Patrones de diseño

| Patrón | Componente | Descripción |
|--------|-----------|-------------|
| Factory | `create_application()` | Crea y configura instancia FastAPI con todas sus dependencias |
| Mediator | `VoiceFlowApp` (app.js) | Coordina AudioHandler, ChatHandler, PipelineVisualizer y DemoModeHandler sin acoplamiento directo |
| Observer | Event listeners (JS) | DOM events, online/offline, MediaRecorder events |
| Template Method | `index.html` (Jinja2) | Template base con variables de contexto y renderizado condicional |
| Module Pattern | `VoiceFlowApp` global | Namespace global para evitar colisiones, encapsula estado |
| Strategy | `CardRenderer` (cards.js) | Métodos estáticos intercambiables para renderizar venue/accessibility/route cards desde el mismo entry point `render()` |

## 10. Estrategia de testing

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

# Test demo scenarios endpoint
def test_demo_scenarios_endpoint(test_client):
    response = test_client.get("/api/v1/chat/demo/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) >= 4

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

# Test static files (incluyendo nuevos JS)
def test_static_files_accessible(test_client):
    for path in ["/static/css/app.css", "/static/js/app.js",
                 "/static/js/cards.js", "/static/js/pipeline.js",
                 "/static/js/demo.js"]:
        response = test_client.get(path)
        assert response.status_code == 200

# Test docs condicionales
def test_docs_disabled_in_production():
    # Con debug=False, /api/docs debe retornar 404
```

## 11. Deuda técnica identificada

1. **Variables de contexto Jinja2 incorrectas:** `index.html` usa `{{ title }}` y `{{ environment }}`, pero la ruta `GET /` pasa `app_name`, `app_description`, `version`, `debug`. Las variables `title` y `environment` se renderizarían vacías.
2. **Templates 404/500 no conectados:** `404.html` y `500.html` existen pero no hay handlers que los sirvan; FastAPI retorna JSON por defecto en errores.
3. **Logging configurado como side effect:** `structlog.configure()` y `logging.basicConfig()` se ejecutan al importar `fastapi_factory.py`, lo que dificulta testing y reconfigurabilidad.
4. **`server_launcher.py` duplica funcionalidad de `run-ui.py`:** Ambos scripts hacen esencialmente lo mismo. `server_launcher.py` añade validación de dependencias y parsing `.env` manual (ya soportado por Pydantic `BaseSettings`).
5. **`sys.path.insert` en `server_launcher.py`:** Apunta a `presentation/` en vez de la raíz del proyecto. Funciona por casualidad porque `run-ui.py` ya configura el path.
6. **CDN sin fallback:** Bootstrap CSS/JS se cargan desde CDN sin fallback local. Si el CDN falla, la UI se rompe completamente.
7. **`initialize_services()` crea instancias duplicadas:** Como se documenta en el SDD de shared/, las instancias globales creadas en startup no se usan (el DI por request crea las suyas).
8. **Sin CSP ni headers de seguridad:** No se configura Content-Security-Policy, X-Frame-Options, ni otros headers de seguridad HTTP.
9. **`conversation_id` generado en frontend:** El ID se genera con `Date.now() + Math.random()`, lo cual no es criptográficamente seguro ni globalmente único. Debería generarse en el backend con UUID.
