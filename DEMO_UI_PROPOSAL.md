# Demo UI Enhancement Proposal

**Target audience:** Investors / Stakeholders (non-technical)
**Timeframe:** 1-2 weeks
**Stack:** Vanilla JS + Bootstrap (no new frameworks)
**Goal:** Visual polish + showcase AI pipeline capabilities

---

## Context

The current UI shows the full audio → transcription → chat flow, but renders
everything as plain text in a chat bubble. The backend already returns rich
structured data (intent, entities, accessibility scores, routes, venue details)
that is completely invisible to the user.

The key opportunity is **making the AI pipeline visible** — investors should
*see* the intelligence working, not just read a text response.

---

## Proposed Features

### F1 — Agent Pipeline Visualizer
**Impact: high | Effort: medium**

A horizontal step indicator that lights up in real-time as each agent
processes the request:

```
[NLU] → [Accessibility] → [Routes] → [Venue Info] → [Response]
  ✅        ⏳ loading...       ○           ○              ○
```

- Each step transitions: idle → processing (pulse animation) → done (checkmark)
- Shows processing time per step
- Placed between the transcription panel and the chat panel
- Data source: extend `/api/v1/chat/message` response to include `pipeline_steps`
  with timing per tool, or mock it client-side with sequential delays

**Why it matters:** Investors see that this is not a simple ChatGPT wrapper —
it's a multi-agent orchestration system with specialized tools.

---

### F2 — Rich Response Cards
**Impact: high | Effort: medium**

Instead of plain text, render structured cards inside the chat when the
backend returns tourism data:

- **Venue Card**: Name, accessibility score (circular gauge), opening hours,
  pricing, key facilities as icon badges
- **Route Card**: Transport mode icon, duration, step-by-step accordion,
  accessibility features as chips
- **Accessibility Summary Card**: Score gauge (0-10), facility list with
  icons, certifications

Cards use existing Bootstrap `.card` components with custom styling.
Data source: parse `tourism_data` from the chat response, or mock with
predefined JSON for demo venues.

**Why it matters:** Transforms a "text chatbot" into an "intelligent travel
assistant" — the visual leap is immediate.

---

### F3 — Animated Voice Waveform
**Impact: medium | Effort: low**

Replace the current frequency bar visualizer with a smooth, organic waveform
similar to Siri/ChatGPT voice mode:

- Idle state: subtle breathing wave
- Recording: reactive amplitude wave with gradient colors
- Processing: morphs into a loading animation
- Pure CSS + Canvas, no libraries

**Why it matters:** First thing the investor sees. Sets the tone for
a polished, modern product.

---

### F4 — Live Transcription Effect
**Impact: medium | Effort: low**

When the transcription result arrives, display it word-by-word with a
typewriter animation instead of showing the full text at once.

- Words appear sequentially (40-60ms per word)
- Subtle fade-in per word
- Confidence indicator fills progressively
- Works with both real and simulated transcription

**Why it matters:** Creates a "wow" moment — the investor watches the
AI "understanding" the speech in real-time.

---

### F5 — Intent & Entity Chips
**Impact: medium | Effort: low**

After the assistant responds, show extracted metadata as visual chips
below the message:

```
┌─────────────────────────────────────────────┐
│ Assistant response text here...              │
│                                             │
│ Intent: [venue_search]                      │
│ Entities: [Museo del Prado] [silla]         │
│ Confidence: ████████░░ 85%                  │
│ 1.2s                                        │
└─────────────────────────────────────────────┘
```

Data source: `intent` and `entities` fields already returned by the API.

**Why it matters:** Shows the NLU intelligence without the investor
needing to understand what NLU is.

---

### F6 — Demo Mode with Guided Scenarios
**Impact: high | Effort: medium**

A "Start Demo" overlay that offers 3-4 predefined scenarios the presenter
can trigger with one click:

1. "Quiero visitar el Museo del Prado en silla de ruedas"
2. "¿Cómo llego al Museo Reina Sofía en transporte accesible?"
3. "Recomiéndame restaurantes accesibles en el centro"
4. "Quiero ir a un concierto, necesito acceso auditivo"

Each scenario:
- Auto-fills the transcription (with typewriter effect from F4)
- Triggers the pipeline visualization (F1)
- Renders rich response cards (F2)
- Works without API keys (pre-built responses)

Can also be used with real APIs when available (toggle in UI).

**Why it matters:** Removes demo risk. The presenter always has a
reliable path, and each scenario showcases different capabilities.

---

### F7 — Dark Theme
**Impact: low | Effort: low**

Toggle between light and dark themes. Dark mode is already partially
supported via CSS variables. Add a toggle button in the navbar.

- Swap CSS custom properties
- Store preference in localStorage
- Dark theme as default for demo (more visually striking on projector)

**Why it matters:** Quick win. Dark UIs look more "tech" and modern
for investor presentations.

---

## Prioritization

| Priority | Feature | Effort | Visual Impact | Showcases AI |
|----------|---------|--------|---------------|-------------|
| P0       | F6 — Demo Scenarios    | Medium | ★★★★★ | ★★★★★ |
| P0       | F1 — Pipeline Viz      | Medium | ★★★★★ | ★★★★★ |
| P0       | F2 — Rich Cards        | Medium | ★★★★★ | ★★★★☆ |
| P1       | F4 — Typewriter Effect | Low    | ★★★★☆ | ★★★☆☆ |
| P1       | F5 — Intent Chips      | Low    | ★★★☆☆ | ★★★★★ |
| P1       | F3 — Voice Waveform    | Low    | ★★★★☆ | ★★☆☆☆ |
| P2       | F7 — Dark Theme        | Low    | ★★★☆☆ | ★☆☆☆☆ |

**Recommended implementation order:** F6 → F1 → F2 → F4 → F5 → F3 → F7

Rationale: F6 (demo scenarios) is the foundation — it ensures a reliable
demo flow. F1 and F2 are the core "wow factor" features that make the AI
visible. The rest are polish layers built on top.

---

## Backend Changes Required (minimal)

| Change | Scope | Purpose |
|--------|-------|---------|
| Add `pipeline_steps` to chat response | `backend_adapter.py` | Timing data for F1 pipeline viz |
| Add `entities` parsing to response | Already exists | Used by F5 intent chips |
| Add `/api/v1/chat/demo/scenarios` | New endpoint | Pre-built scenario data for F6 |
| Mock tourism_data in simulation mode | `backend_adapter.py` | Rich card data when no API keys |

All changes are additive — no modifications to existing business logic.

---

## References & Inspiration

- **ChatGPT Voice Mode**: Organic waveform animation, real-time feel
- **Google Assistant**: Step-by-step action cards, structured responses
- **Apple Siri**: Minimalist waveform, typewriter transcription
- **Booking.com / Google Travel**: Venue cards with ratings and accessibility info
- **Linear App**: Pipeline status visualizations, dark theme

---
---

# Software Design Document — P0 Implementation

## 1. UI Technology Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| **CSS Framework** | Bootstrap | 5.3.0 | CDN (`cdn.jsdelivr.net`) |
| **Icon Library** | Bootstrap Icons | 1.11.0 | CDN, class-based (`bi-*`) |
| **JavaScript** | Vanilla ES2022 | — | No framework, no build step, no transpiler |
| **Templating** | Jinja2 | (via FastAPI) | Server-side rendering for `index.html` |
| **Static Serving** | FastAPI `StaticFiles` | — | Mounted at `/static/` |
| **CSS Architecture** | Single file | `app.css` | CSS custom properties (`:root` vars), no preprocessor |
| **JS Architecture** | Class-based modules | 6 files | Each class exported via `window.*`, loaded via `<script>` tags |
| **Package Manager** | None (frontend) | — | All dependencies loaded from CDN |
| **Build Tools** | None (frontend) | — | No bundler, no minification, no tree-shaking |

**Design decisions:**
- No build pipeline — edit a `.js` or `.css` file and reload. Docker volume mounts + uvicorn `--reload` enable instant feedback.
- No framework (React, Vue, etc.) — keeps the POC lightweight and avoids toolchain complexity for a demo-focused project.
- ES2022 features used: `static` class fields (`CardRenderer`), optional chaining (`?.`), `async/await`. All supported in Chrome 72+, Firefox 75+, Safari 14.1+.
- All JS classes are self-contained and communicate through the `window.VoiceFlowApp` singleton (no event bus, no state management library).

---

## 2. Implementation Overview

This section documents the implemented P0 features: **F6 (Demo Scenarios)**, **F1 (Pipeline Visualizer)**, and **F2 (Rich Response Cards)**. These three features work together to provide a reliable, visually rich demo flow that showcases the multi-agent AI pipeline to investors.

### Implementation Status

| Feature | Status | Files Created | Files Modified |
|---------|--------|---------------|----------------|
| F6 — Demo Scenarios | Implemented | `demo.js` | `chat.py`, `backend_adapter.py`, `app.js`, `index.html`, `app.css` |
| F1 — Pipeline Visualizer | Implemented | `pipeline.js` | `responses.py`, `app.js`, `index.html`, `app.css` |
| F2 — Rich Response Cards | Implemented | `cards.js` | `chat.js`, `app.css` |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (Vanilla JS + Bootstrap 5)                             │
│                                                                 │
│  ┌──────────────┐  ┌───────────────────┐  ┌──────────────────┐  │
│  │ DemoMode     │→ │ PipelineVisualizer│→ │ CardRenderer     │  │
│  │ Handler      │  │                   │  │ (static methods) │  │
│  │ (demo.js)    │  │ (pipeline.js)     │  │ (cards.js)       │  │
│  └──────┬───────┘  └─────────┬─────────┘  └────────┬─────────┘  │
│         │                    │                      │            │
│         ▼                    ▼                      ▼            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ChatHandler (chat.js)                  │   │
│  │  sendMessage() → pipeline.startAnimation()                │   │
│  │  addMessage()  → CardRenderer.render(tourismData)         │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────┴───────────────────────────────┐   │
│  │                  VoiceFlowApp (app.js)                    │   │
│  │  Orchestrator — initializes all components                │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────┘
                              │ HTTP
┌─────────────────────────────┼───────────────────────────────────┐
│  FastAPI Backend             │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              /api/v1/chat/message (POST)                  │   │
│  │              /api/v1/chat/demo/scenarios (GET)             │   │
│  │                      (chat.py)                            │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────┴───────────────────────────────┐   │
│  │           LocalBackendAdapter (backend_adapter.py)        │   │
│  │  process_query() → _simulate_ai_response()                │   │
│  │                  → _get_simulation_metadata()              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Initialization Sequence

```
DOMContentLoaded
  └→ VoiceFlowApp.init()
       └→ initializeComponents()
            ├→ new AudioHandler()           [existing]
            ├→ new ChatHandler()            [existing]
            ├→ new PipelineVisualizer()     [NEW — F1]
            │    └→ .init() → buildUI() → inserts into DOM (hidden)
            └→ new DemoModeHandler()        [NEW — F6]
                 └→ await .init()
                      ├→ loadScenarios()    fetch /api/v1/chat/demo/scenarios
                      ├→ buildDemoBar()     inserts into DOM (visible)
                      └→ setupNavbarToggle()
```

Each component is wrapped in its own `try-catch` so a failure in one does not
prevent the others from initializing.

### 3.3 Script Loading Order

Defined in `presentation/templates/index.html`:

```html
<script src="/static/js/audio.js"></script>
<script src="/static/js/chat.js"></script>
<script src="/static/js/cards.js"></script>      <!-- NEW — F2 -->
<script src="/static/js/pipeline.js"></script>   <!-- NEW — F1 -->
<script src="/static/js/demo.js"></script>       <!-- NEW — F6 -->
<script src="/static/js/app.js"></script>
```

Order matters: `cards.js` must load before `chat.js` uses `CardRenderer`,
and `pipeline.js`/`demo.js` must load before `app.js` instantiates them.

---

## 4. Demo Flow (end-to-end)

When the presenter clicks a demo scenario button:

```
1. Click "Museo del Prado accesible"
   │
2. DemoModeHandler.runScenario(0)
   ├→ Clear chat + reset pipeline
   ├→ typewriterEffect(query)          word-by-word in transcription box (~1.5s)
   ├→ chatHandler.addMessage('user')   user bubble appears in chat
   │
3. ├→ [parallel]
   │   ├→ chatHandler.sendToBackend()  POST /api/v1/chat/message
   │   └→ pipeline.startAnimation()    5 steps animate sequentially (~3.2s)
   │
4. ├→ pipeline.completeFromResponse()  snap timings from server data
   │
5. └→ chatHandler.addMessage('assistant', response, {tourismData})
        └→ CardRenderer.render()       venue card + accessibility card + route cards
```

The "Real API" toggle switches between:
- **Off (default)**: Backend simulation mode, pipeline animation runs with default timings
- **On**: Sends to real LangChain agents, pipeline completes from actual response data

---

## 5. New Files

### 6.1 `presentation/static/js/demo.js` — DemoModeHandler

**Purpose:** Provides guided demo scenario buttons with orchestrated animations.

**Class:** `DemoModeHandler`

| Method | Description |
|--------|-------------|
| `async init()` | Loads scenarios from API, builds DOM, sets up navbar toggle |
| `async loadScenarios()` | Fetches `GET /api/v1/chat/demo/scenarios`, falls back to hardcoded |
| `getFallbackScenarios()` | Returns 4 hardcoded scenarios (Prado, Reina Sofia, restaurants, concerts) |
| `buildDemoBar()` | Creates card with scenario buttons + "Real API" toggle, injects into DOM |
| `setupNavbarToggle()` | Adds "Demo" link in navbar to collapse/expand the demo bar |
| `toggleDemoBar()` | Toggles `d-none` on scenario buttons container |
| `async runScenario(index)` | Full orchestration: clear → typewriter → pipeline → cards |
| `async typewriterEffect(text)` | Word-by-word animation (60ms/word) with blinking cursor |

**DOM injection point:**
```javascript
const mainContainer = document.querySelector('.container-fluid > .container');
const mainInterface = mainContainer.querySelector(':scope > .row:not(.mb-4)');
mainContainer.insertBefore(this.container, mainInterface);
```

**UI structure:**
```
┌──────────────────────────────────────────────────────────────┐
│  ▶ Demo Scenarios                      [Real API toggle] [▲] │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────┐ ┌────────┐ │
│  │ Museo Prado  │ │ Reina Sofia   │ │ Restaur. │ │ Concier│ │
│  └──────────────┘ └───────────────┘ └──────────┘ └────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

### 6.2 `presentation/static/js/pipeline.js` — PipelineVisualizer

**Purpose:** 5-step horizontal indicator showing multi-agent processing progress.

**Class:** `PipelineVisualizer`

| Method | Description |
|--------|-------------|
| `init()` | Calls `buildUI()` |
| `buildUI()` | Creates 5 step elements with icons + connectors, injects into DOM (hidden) |
| `reset()` | Sets all steps to `idle`, clears timings, resets connector fills |
| `async startAnimation(pipelineSteps)` | Sequential animation: idle → processing → completed per step |
| `completeFromResponse(response)` | Instantly completes all steps using server-provided `pipeline_steps` data |

**Pipeline steps configuration:**

| Step | Icon | Tool ID |
|------|------|---------|
| NLU | `bi-brain` | `tourism_nlu` |
| Accessibility | `bi-universal-access` | `accessibility_analysis` |
| Routes | `bi-map` | `route_planning` |
| Venue Info | `bi-info-circle` | `tourism_info` |
| Response | `bi-chat-square-text` | `llm_synthesis` |

**Step states:**

| State | CSS Class | Visual |
|-------|-----------|--------|
| idle | `.pipeline-step.idle` | Dimmed icon, muted colors |
| processing | `.pipeline-step.processing` | Cyan pulse animation, active glow |
| completed | `.pipeline-step.completed` | Green icon, checkmark, shows duration |

**Animation timing (defaults):** `[450, 620, 880, 540, 710]` ms — total ~3.2s

The container starts hidden (`d-none`) and is revealed on first `startAnimation()` call.

---

### 6.3 `presentation/static/js/cards.js` — CardRenderer

**Purpose:** Renders structured `tourism_data` as Bootstrap cards inside chat messages.

**Class:** `CardRenderer` (all static methods — no instantiation needed)

| Method | Input | Output |
|--------|-------|--------|
| `render(tourismData)` | `{ venue?, accessibility?, routes? }` | HTML string with all applicable cards |
| `renderVenueCard(venue)` | Venue object | Card with name, circular gauge, facility badges, hours, pricing |
| `renderAccessibilityCard(accessibility)` | Accessibility object | Card with score bar, level, certification, services list |
| `renderRouteCards(routes)` | Array of route objects | One card per route with transport icon, steps, cost |
| `escapeHtml(text)` | String | XSS-safe string |

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

**Facility icon mapping:**

| Key | Icon | Label |
|-----|------|-------|
| `wheelchair_ramps` | `bi-person-wheelchair` | Rampas |
| `adapted_bathrooms` | `bi-droplet` | Aseos adaptados |
| `audio_guides` | `bi-headphones` | Audioguias |
| `tactile_paths` | `bi-hand-index` | Rutas tactiles |
| `sign_language_interpreters` | `bi-hand-thumbs-up` | Lengua de signos |
| `elevator_access` | `bi-arrow-up-square` | Ascensor |
| `wheelchair_spaces` | `bi-person-wheelchair` | Espacios reservados |
| `hearing_loops` | `bi-ear` | Bucle auditivo |

**Score color thresholds:** `>= 8` → success (green), `>= 6` → warning (yellow), `< 6` → danger (red)

---

## 6. Modified Files

### 6.1 `application/api/v1/chat.py`

**New endpoint:**

```
GET /api/v1/chat/demo/scenarios
```

Returns 4 predefined scenario definitions:

```json
{
  "success": true,
  "scenarios": [
    { "id": "prado_wheelchair",      "title": "Museo del Prado accesible",  "icon": "bi-building",           "query": "Quiero visitar el Museo del Prado en silla de ruedas" },
    { "id": "reina_sofia_transport",  "title": "Transporte al Reina Sofia",  "icon": "bi-map",                "query": "¿Cómo llego al Museo Reina Sofía...?" },
    { "id": "restaurants_centro",     "title": "Restaurantes accesibles",    "icon": "bi-cup-hot",            "query": "Recomiéndame restaurantes accesibles en el centro" },
    { "id": "concert_hearing",        "title": "Conciertos accesibles",      "icon": "bi-music-note-beamed",  "query": "Quiero ir a un concierto, necesito acceso auditivo" }
  ]
}
```

**Modified `send_message()`:** Now passes `tourism_data`, `pipeline_steps`, `intent`, and `entities` from the backend response to `ChatResponse`.

---

### 6.2 `application/models/responses.py`

**New model:**

```python
class PipelineStep(BaseModel):
    name: str           # Display name (e.g. "NLU")
    tool: str           # Tool identifier (e.g. "tourism_nlu")
    status: str         # "pending" | "processing" | "completed" | "error"
    duration_ms: int    # Processing time in milliseconds
    summary: str        # Brief output summary
```

**Extended `ChatResponse`:**

```python
class ChatResponse(BaseResponse):
    # ... existing fields ...
    tourism_data:   Optional[Dict[str, Any]]       # Structured venue/route/accessibility data
    intent:         Optional[str]                   # Detected user intent
    entities:       Optional[Dict[str, Any]]        # Extracted entities
    pipeline_steps: Optional[List[Dict[str, Any]]]  # Per-tool step timing and status
```

---

### 6.3 `application/orchestration/backend_adapter.py`

**New method: `_get_simulation_metadata(query_lower)`**

Returns `pipeline_steps`, `tourism_data`, `intent`, and `entities` for simulation mode based on keyword matching.

**Keyword routing:**

| Keywords | Intent | Tourism Data |
|----------|--------|-------------|
| `prado`, `museo del prado` | `venue_search` | Full Prado venue + 2 routes + accessibility (9.2/10) |
| `reina`, `sofía`, `sofia` | `route_search` | Reina Sofia venue + 2 routes + accessibility (8.8/10) |
| `concierto`, `música`, `musica` | `event_search` | Music venues + 1 route + accessibility (7.5/10) |
| `restaurante`, `comer`, `comida` | `recommendation` | Restaurant info + 1 route + accessibility (6.5/10) |
| _(default)_ | `general_query` | No tourism_data (null) |

Each scenario returns 5 pipeline steps with customized summaries:

```python
[
    {"name": "NLU",           "tool": "tourism_nlu",          "duration_ms": 450, ...},
    {"name": "Accessibility", "tool": "accessibility_analysis","duration_ms": 620, ...},
    {"name": "Routes",        "tool": "route_planning",       "duration_ms": 880, ...},
    {"name": "Venue Info",    "tool": "tourism_info",          "duration_ms": 540, ...},
    {"name": "Response",      "tool": "llm_synthesis",         "duration_ms": 710, ...},
]
```

---

### 6.4 `presentation/static/js/chat.js`

**Modified `sendMessage()`:**

Before sending to backend, starts the pipeline animation:

```javascript
const pipelineViz = window.VoiceFlowApp?.pipelineVisualizer;
if (pipelineViz) pipelineViz.startAnimation(null);
```

After receiving response, updates pipeline with actual server timings and passes
rich metadata to `addMessage()`:

```javascript
if (pipelineViz && response.pipeline_steps) {
    pipelineViz.completeFromResponse(response);
}
this.addMessage('assistant', response.ai_response, {
    processingTime: response.processing_time,
    tourismData: response.tourism_data,
    pipelineSteps: response.pipeline_steps,
});
```

**Modified `addMessage()`:**

- Adds `has-cards` CSS class to assistant messages that have `tourismData` (wider layout)
- Calls `CardRenderer.render(metadata.tourismData)` to append rich cards after message text
- Renders a `.message-meta` div with timestamp + processing time

---

### 6.5 `presentation/static/js/app.js`

**New global state properties:**

```javascript
pipelineVisualizer: null,
demoHandler: null,
```

**Modified `initializeComponents()`:**

Each component initialization is wrapped in its own `try-catch` for fault isolation:

```javascript
try {
    this.pipelineVisualizer = new PipelineVisualizer();
    this.pipelineVisualizer.init();
} catch (e) { console.error('PipelineVisualizer init failed:', e); }

try {
    this.demoHandler = new DemoModeHandler();
    await this.demoHandler.init();
} catch (e) { console.error('DemoModeHandler init failed:', e); }
```

---

### 6.6 `presentation/static/css/app.css`

~400 lines appended, organized in three sections:

#### F6 — Demo Mode Styles (lines 317-389)

| Selector | Purpose |
|----------|---------|
| `.demo-scenarios-card` | Dashed border container for demo bar |
| `.demo-bar-title` | Title with icon styling |
| `.demo-scenario-btn` | Pill-shaped scenario buttons with hover effects |
| `.demo-scenario-btn.active` | Blue pulse animation on active scenario |
| `.typewriter-cursor` | Blinking cursor during typewriter effect |
| `.typewriter-word` | Fade-in animation per word |
| `@keyframes pulse-blue` | Active button pulse animation |
| `@keyframes blink` | Cursor blink animation |

#### F1 — Pipeline Visualizer Styles (lines 391-493)

| Selector | Purpose |
|----------|---------|
| `.pipeline-container` | Dark gradient background with rounded corners |
| `.pipeline-step` | Flex column with icon circle + label + time |
| `.pipeline-step-icon` | 48px circle with border and centered icon |
| `.pipeline-step.idle` | Muted colors, dimmed icon |
| `.pipeline-step.processing` | Cyan border + pulse animation + glow shadow |
| `.pipeline-step.completed` | Green border + icon, visible time label |
| `.pipeline-connector` | Horizontal line between steps (gray background) |
| `.pipeline-connector-fill` | Animated cyan fill that grows left-to-right |
| `@keyframes pipeline-pulse` | Scale oscillation for processing state |

#### F2 — Rich Response Card Styles (lines 495-684)

| Selector | Purpose |
|----------|---------|
| `.response-cards` | Container with slide-in animation |
| `.response-card` | White card with left color accent border |
| `.venue-card` | Blue left border |
| `.accessibility-card` | Green left border |
| `.route-card` | Info/cyan left border |
| `.gauge-circle` | 56x56px circular score indicator |
| `.gauge-value` / `.gauge-label` | Score number and "/10" label |
| `.facility-badge` | Pill badge with icon for each facility |
| `.score-bar` / `.score-bar-fill` | Horizontal progress bar for accessibility score |
| `.route-step` | Numbered step with left-border connector line |
| `.route-step-number` | Circular step number indicator |
| `.message-meta` | Timestamp + processing time footer on messages |
| `@keyframes cardSlideIn` | Slide-up + fade-in entry animation |
| `.has-cards` | Expands message max-width to 95% for card layout |

#### Responsive Overrides (lines 686-719)

`@media (max-width: 768px)`:
- Pipeline steps shrink (smaller icons, abbreviated labels)
- Demo buttons use `btn-sm`
- Gauge circles scale down

---

## 7. Data Contracts

### 7.1 tourism_data Object Shape

```typescript
interface TourismData {
  venue?: {
    name: string;
    type: string;                           // "museum" | "entertainment" | "restaurant"
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

### 7.2 pipeline_steps Array Shape

```typescript
interface PipelineStep {
  name: string;         // Display name
  tool: string;         // Tool identifier
  status: string;       // "pending" | "processing" | "completed" | "error"
  duration_ms: number;  // Milliseconds
  summary: string;      // Brief description of step output
}
```

---

## 8. DOM Injection Strategy

Both `DemoModeHandler` and `PipelineVisualizer` inject themselves dynamically
into the DOM. The insertion target is the main content area, between the status
bar and the main two-column interface.

**Selector chain:**

```javascript
// 1. Find the main content container (skip the <nav>'s .container)
const mainContainer = document.querySelector('.container-fluid > .container');

// 2. Find the first direct-child .row without .mb-4 (= main interface)
const mainInterface = mainContainer.querySelector(':scope > .row:not(.mb-4)');

// 3. Insert before it
mainContainer.insertBefore(element, mainInterface);
```

**Why `:scope >`:** The HTML contains nested `.row` elements inside Bootstrap
cards (e.g., `<div class="row align-items-center">` inside the status bar).
Without `:scope >`, `querySelector` matches the first `.row:not(.mb-4)` in
the entire subtree — which is the nested one, not the main interface row.

**Resulting DOM order:**

```
.container-fluid
  └ nav.navbar
      └ .container          ← skipped (not direct child of .container-fluid)
  └ .container              ← mainContainer
      ├ .row.mb-4           ← Status bar
      ├ #demoBar.row.mb-4   ← Demo bar (injected by DemoModeHandler)
      ├ #pipelineVisualizer.row.mb-4.d-none  ← Pipeline (injected, hidden until animation)
      ├ .row                ← Main interface (mainInterface reference)
      └ .row.mt-4           ← Debug panel (if debug mode)
```

---

## 9. Error Handling

### Frontend

- **Component isolation:** Each component in `app.js` is wrapped in its own
  `try-catch`. A failure in `PipelineVisualizer` does not prevent `DemoModeHandler`
  from loading (and vice versa).
- **DOM null-safety:** Both `pipeline.js` and `demo.js` check for null before
  DOM operations and return early with a console warning.
- **Scenario fallback:** `DemoModeHandler.loadScenarios()` catches fetch errors
  and falls back to hardcoded scenarios.
- **Demo error recovery:** `runScenario()` has a `try/catch/finally` that always
  re-enables buttons, even if the scenario fails mid-execution.

### Backend

- **Graceful degradation:** `_get_simulation_metadata()` returns `tourism_data: None`
  for unrecognized queries. The frontend renders no cards in this case.
- **Field optionality:** All new `ChatResponse` fields (`tourism_data`, `pipeline_steps`,
  `intent`, `entities`) are `Optional` with `default=None`.

---

## 10. How to Test

1. Start the application:
   ```bash
   docker compose up
   ```

2. Open `http://localhost:8000` in a modern browser

3. **Demo bar** should be visible below the status bar with 4 scenario buttons

4. **Click any scenario button:**
   - Typewriter fills the transcription box (~1.5s)
   - User message appears in chat
   - Pipeline steps animate sequentially (~3.2s)
   - Assistant message appears with rich cards (venue + accessibility + routes)

5. **Manual chat:** Type a query in the input box (e.g., "Museo del Prado") and
   press Enter. Pipeline animates and response includes cards if keywords match.

6. **Real API toggle:** Switch "Real API" on to send queries to the actual
   LangChain multi-agent system (requires API keys in `.env`).

7. **Responsive:** Resize browser to mobile width — pipeline and cards should
   adapt gracefully.

8. **Console:** Open DevTools (F12) — no errors should appear. Each component
   logs a confirmation message on successful initialization.
