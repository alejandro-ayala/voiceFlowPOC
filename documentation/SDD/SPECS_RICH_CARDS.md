# Spec: Rich Data Contract & Component Rendering (F2)

**Contexto:** VoiceFlow PoC — Sistema de Turismo Accesible
**Objetivo:** Contrato de datos entre el `LocalBackendAdapter` (Capa 2) y el `CardRenderer` (Capa 1) para Rich Response Cards.
**Actualizado:** 2026-02-16 — Alineado con implementacion real (post-auditoria SDD)

---

## 1. Contrato de Datos (Schema)

### 1.1 Estructura del Objeto `tourism_data`

Toda respuesta de la IA que detecte una intencion de busqueda, ruta o accesibilidad **debe** incluir este objeto en el cuerpo de la respuesta JSON. Todos los campos de segundo nivel (`venue`, `routes`, `accessibility`) son **opcionales** — el frontend renderiza solo las secciones presentes.

```json
{
  "intent": "venue_search | route_search | event_search | recommendation | general_query",
  "tourism_data": {
    "venue": {
      "name": "string (required)",
      "type": "museum | restaurant | park | entertainment | city_guide | guide",
      "accessibility_score": "number (0-10)",
      "certification": "string | null",
      "facilities": ["string"],
      "description": "string | null",
      "opening_hours": { "key": "value" },
      "pricing": { "key": "value" }
    },
    "routes": [
      {
        "transport": "metro | bus | walking | taxi",
        "line": "string | null",
        "duration": "string",
        "accessibility": "full | partial",
        "cost": "string | null",
        "steps": ["string"]
      }
    ],
    "accessibility": {
      "level": "string",
      "score": "number (0-10)",
      "certification": "string | null",
      "facilities": ["string"],
      "services": { "key": "value" }
    }
  }
}
```

### 1.2 Detalle de campos

#### `venue` (opcional)

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `name` | string | Si | Nombre del lugar |
| `type` | string | No | Categoria: `museum`, `restaurant`, `park`, `entertainment`, `city_guide`, `guide` |
| `accessibility_score` | number | No | Puntuacion de accesibilidad (0-10). Validado: se clampea a [0, 10] |
| `certification` | string \| null | No | Certificacion (e.g. `ONCE_certified`, `municipal_certified`) |
| `facilities` | string[] | No | Keys de facilidades (ver seccion 1.3). Max 20 items |
| `description` | string \| null | No | Descripcion breve del lugar |
| `opening_hours` | dict | No | Horarios como pares clave-valor (e.g. `{"monday_saturday": "10:00-20:00"}`) |
| `pricing` | dict | No | Precios como pares clave-valor (e.g. `{"general": "15€", "reduced": "7.50€"}`) |

#### `routes[]` (opcional, array)

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `transport` | string | No | Modo: `metro`, `bus`, `taxi`, `walking` |
| `line` | string \| null | No | Identificador de linea (e.g. `Metro Line 2`, `Bus 27`) |
| `duration` | string | No | Duracion estimada (e.g. `25 min`) |
| `accessibility` | string | No | Nivel de accesibilidad: `full` o `partial` |
| `cost` | string \| null | No | Coste del trayecto (e.g. `2.50€`) |
| `steps` | string[] | No | Pasos ordenados de la ruta. Max 50 items |

#### `accessibility` (opcional)

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `level` | string | No | Nivel descriptivo (e.g. `full_wheelchair_access`, `partial_access`) |
| `score` | number | No | Puntuacion (0-10). Validado: se clampea a [0, 10] |
| `certification` | string \| null | No | Certificacion de accesibilidad |
| `facilities` | string[] | No | Keys de facilidades. Max 20 items |
| `services` | dict | No | Servicios disponibles como pares clave-valor |

### 1.3 Facility Keys e Iconografia

Keys reconocidos por `CardRenderer.FACILITY_ICONS`:

| Key | Icono Bootstrap | Label UI |
|-----|----------------|----------|
| `wheelchair_ramps` | `bi-person-wheelchair` | Rampas |
| `adapted_bathrooms` | `bi-droplet` | Aseos adaptados |
| `audio_guides` | `bi-headphones` | Audioguias |
| `tactile_paths` | `bi-hand-index` | Rutas tactiles |
| `sign_language_interpreters` | `bi-hand-thumbs-up` | Lengua de signos |
| `elevator_access` | `bi-arrow-up-square` | Ascensor |
| `wheelchair_spaces` | `bi-person-wheelchair` | Espacios reservados |
| `hearing_loops` | `bi-ear` | Bucle auditivo |

Keys no reconocidos se renderizan con icono generico `bi-check-circle` y label derivado del key (underscores → espacios).

### 1.4 Transport Icons

| Transport | Icono Bootstrap |
|-----------|----------------|
| `metro` | `bi-train-front` |
| `bus` | `bi-bus-front` |
| `taxi` | `bi-taxi-front` |
| `walking` | `bi-person-walking` |

Transporte no reconocido usa icono fallback `bi-signpost-2`.

### 1.5 Score Color Thresholds

| Score | Color | CSS class |
|-------|-------|-----------|
| >= 8 | Verde (success) | `gauge-success`, `bg-success` |
| >= 6 | Amarillo (warning) | `gauge-warning`, `bg-warning` |
| < 6 | Rojo (danger) | `gauge-danger`, `bg-danger` |

---

## 2. Logica de Negocio (Business Layer — Capa 3)

* **Extraccion Determinista:** Los agentes de LangChain deben mapear los hallazgos de las herramientas (`TourismTool`, `MapsTool`) a este esquema.
* **Integridad y Anti-Alucinacion:** Si una herramienta no devuelve un dato especifico, el campo debe ser `null`. **Prohibido** inventar o aproximar datos no presentes en el contexto.

---

## 3. Logica de Presentacion (Presentation Layer — Capa 1)

### 3.1 Patron de Renderizado

* **Responsabilidad Unica (S):** `CardRenderer` (`cards.js`) transforma el JSON del contrato en HTML Bootstrap 5.3. Todas sus metodos son `static` — no requiere instanciacion.
* **Extensibilidad (O):** Nuevos tipos de card se anaden como metodos `static renderXxxCard()` sin modificar `render()` ni `chat.js`.

### 3.2 Cards renderizadas

| Seccion `tourism_data` | Metodo | Card CSS class | Borde izquierdo |
|------------------------|--------|---------------|-----------------|
| `venue` | `renderVenueCard()` | `.venue-card` | Azul (`--primary-color`) |
| `accessibility` | `renderAccessibilityCard()` | `.accessibility-card` | Verde (`--success-color`) |
| `routes[]` | `renderRouteCards()` | `.route-card` (1 per route) | Cyan (`--info-color`) |

### 3.3 Mapeo de UI

| Campo | Componente UI | Visual |
|-------|--------------|--------|
| `venue.accessibility_score` | `.gauge-circle` (56x56 circular) | Color dinamico segun threshold |
| `venue.facilities` | Flex-container de `.badge.facility-badge` | Icono + label por facility |
| `venue.opening_hours` | `.venue-detail` con `bi-clock` | Pares clave-valor inline |
| `venue.pricing` | `.venue-detail` con `bi-tag` | Pares clave-valor inline |
| `accessibility.score` | `.score-bar` + `.score-bar-fill` | Barra horizontal con % |
| `accessibility.services` | `.service-item` con `bi-check2` | Lista vertical key: value |
| `routes[].steps` | `.route-step` con `.route-step-number` | Pasos numerados |

---

## 4. Validacion Defensiva

### Backend (Capa 2)

| Validacion | Ubicacion | Comportamiento |
|-----------|-----------|---------------|
| `tourism_data` invalido | `backend_adapter.py` → `TourismData.parse_obj()` | Se dropea a `null`, log warning |
| `pipeline_steps` invalidos | `backend_adapter.py` → `PipelineStep.parse_obj()` por step | Steps invalidos se omiten |
| `accessibility_score` fuera de rango | `Venue` / `Accessibility` validators | Se clampea a [0, 10] |
| `facilities` no es lista | `Venue` / `Accessibility` validators | Se parsea comma-separated string |

### Frontend (Capa 1)

| Validacion | Ubicacion | Comportamiento |
|-----------|-----------|---------------|
| `tourism_data` nulo | `chat.js` → `addMessage()` | Renderiza texto plano, sin cards |
| `CardRenderer` no disponible | `chat.js` → `typeof CardRenderer !== 'undefined'` | Fallback a texto plano |
| Campos opcionales ausentes | `cards.js` → `\|\|`, `?.`, ternarios | Secciones omitidas o valores fallback |
| XSS en strings | `CardRenderer.escapeHtml()` | Escape de `& < > " '` |

---

## 5. Pydantic Models (Capa 2)

Definidos en `application/models/responses.py`:

* `Venue(BaseModel)` — con validators para `accessibility_score` y `facilities`
* `Route(BaseModel)` — con validator para `steps`
* `Accessibility(BaseModel)` — con validators para `score` y `facilities`
* `TourismData(BaseModel)` — con `root_validator` para normalizar `routes`
* `ChatResponse(BaseResponse)` — incluye `tourism_data: Optional[TourismData]`
