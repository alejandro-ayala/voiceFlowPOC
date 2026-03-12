# Plan de Adaptación: UI de Recomendaciones — POC a Producción

**Fecha**: 12 de Marzo de 2026
**Versión**: 1.0
**Estado**: PENDIENTE DE REVISIÓN
**Autor**: Claude Opus 4.6
**Objetivo**: Transformar la capa de presentación (tarjetas de recomendación) desde POC a arquitectura production-ready

---

## Índice

1. [Análisis del Problema Actual](#1-análisis-del-problema-actual)
2. [Propuesta de Nuevo Contrato de Datos](#2-propuesta-de-nuevo-contrato-de-datos)
3. [Arquitectura Recomendada](#3-arquitectura-recomendada)
4. [Diseño de la Representación en UI](#4-diseño-de-la-representación-en-ui)
5. [Plan de Migración](#5-plan-de-migración)
6. [Ejemplo Completo](#6-ejemplo-completo)
7. [Checklist de Implementación](#7-checklist-de-implementación)

---

## Documentos de Referencia

| Documento | Relevancia |
|-----------|------------|
| `ARCHITECTURE_MULTIAGENT.md` | Flujo de datos del pipeline multi-agente |
| `ARCHITECTURE_VOICE-FLOW-POC.md` | Arquitectura en 4 capas |
| `ESTADO_ACTUAL_SISTEMA.md` | Estado operativo actual (qué funciona y qué no) |
| `API_REFERENCE.md` | Contrato actual del endpoint `POST /api/v1/chat/message` |
| `DEVELOPMENT.md` | Estructura de proyecto y convenciones |
| `ROADMAP.md` | Fases completadas y próximas |

---

## 1. Análisis del Problema Actual

### 1.1 Limitaciones de la Respuesta Actual

Tras auditar el código del sistema completo, se identifican **tres gaps estructurales** que impiden una representación correcta de recomendaciones en la UI:

#### Gap A: `metadata.tool_outputs` solo expone NLU y NER

En `application/orchestration/backend_adapter.py` (líneas 245-249), `stable_tool_outputs` se construye únicamente con `location_ner` y `nlu`. Los datos de dominio (places, accessibility, directions) fluyen por `tourism_data`, que proviene del output del LLM, no directamente de los tool outputs tipados.

```python
# backend_adapter.py — estado actual
stable_tool_outputs: dict[str, Any] = {}
if location_ner_payload:
    stable_tool_outputs["location_ner"] = location_ner_payload
if nlu_payload:
    stable_tool_outputs["nlu"] = nlu_payload
# ❌ NO incluye: places, accessibility, directions
```

**Consecuencia:** La UI no puede acceder a datos estructurados de venues, accesibilidad o rutas desde `tool_outputs`. Depende de `tourism_data`, que es construido de forma menos fiable.

#### Gap B: `tourism_data` es una estructura single-venue, no multi-recomendación

El modelo actual en `application/models/responses.py` define `TourismData` con un solo venue, un solo bloque de accessibility y una lista de routes (todas para ese único venue):

```python
# responses.py — estado actual
class TourismData(BaseModel):
    venue: Optional[Venue] = None            # ← singular
    accessibility: Optional[Accessibility] = None  # ← singular
    routes: Optional[List[Route]] = None
```

**Consecuencia:** Aunque el LLM puede mencionar 3 restaurantes en `ai_response`, la estructura solo transporta datos de 1.

#### Gap C: `ToolPipelineContext` transporta un solo `PlaceCandidate`

En `shared/models/tool_models.py`, el pipeline acumula un solo lugar:

```python
# tool_models.py — estado actual
class ToolPipelineContext(BaseModel):
    place: Optional[PlaceCandidate] = None        # ← singular
    accessibility: Optional[AccessibilityInfo] = None  # ← singular
    routes: list[RouteOption] = []                 # ← todas para un destino
    venue_detail: Optional[VenueDetail] = None     # ← singular
```

**Consecuencia:** Incluso aunque `PlacesSearchTool` pudiera devolver N candidatos, el pipeline no tiene dónde transportarlos.

### 1.2 Flujo Actual de Datos (Donde se Pierde Información)

```
PlacesSearchTool
    → PlaceCandidate (1 lugar)
        → ToolPipelineContext.place (singular)
            → agent._build_metadata() → tourism_data.venue (singular)
                → backend_adapter → TourismData.model_validate() (singular)
                    → CardRenderer.render() → 1 venue card
```

**En cada paso, la cardinalidad es 1.** No hay soporte end-to-end para N recomendaciones.

### 1.3 Problemas de Usar Directamente `metadata.tool_outputs`

| Problema | Descripción |
|----------|-------------|
| Contrato incompleto | Solo expone NLU y NER, no datos de dominio |
| Formato interno | Los datos en `tool_results_parsed` son formatos internos de cada tool, no normalizados para UI |
| Acoplamiento | Si la UI lee directamente tool outputs, cualquier cambio en una tool rompe la UI |
| Sin versionado | No hay contrato estable entre agentes y UI |

### 1.4 Riesgos de Mantener el Diseño Actual

| Riesgo | Impacto | Severidad |
|--------|---------|-----------|
| UI muestra solo 1 venue porque `tourism_data.venue` es singular | UX pobre, no hay comparación entre opciones | **Alto** |
| `tourism_data` depende del JSON que GPT-4 genera en texto libre | Datos inconsistentes, campos faltantes, parsing frágil | **Alto** |
| Cards.js lee `tourismData.venue` (singular), no iterable | Requiere refactor de UI para multi-card | **Medio** |
| Sin Google Maps link en el modelo de datos | Feature de routing incompleta (se trabaja en otra rama) | **Medio** |
| Sin warnings de accesibilidad en cards | Información crítica para el usuario final no visible | **Medio** |

---

## 2. Propuesta de Nuevo Contrato de Datos

### 2.1 Nuevo Modelo: `Recommendation` como Unidad Atómica

Se propone un nuevo campo `recommendations` en la respuesta de la API que reemplaza funcionalmente a `tourism_data`:

```
┌──────────────────────────────────────────────────────────┐
│                    ChatResponse                           │
│                                                           │
│  ai_response: string                                      │
│  recommendations: Recommendation[]        ← NUEVO         │
│  tourism_data: TourismData | null        ← DEPRECAR       │
│  intent, entities, pipeline_steps, metadata               │
└──────────────────────────────────────────────────────────┘
```

Cada `Recommendation` agrupa **toda la información de un lugar**:

```
┌──────────────────────────────────────────────────────────┐
│                   Recommendation                          │
│                                                           │
│  id: string                (place_id o uuid generado)     │
│  name: string              ("Restaurante La Barraca")     │
│  type: string              ("restaurant", "museum", etc.) │
│  summary: string | null    (descripción corta generada)   │
│                                                           │
│  venue: Venue | null                                      │
│  accessibility: Accessibility | null                      │
│  routes: Route[]                                          │
│                                                           │
│  maps_url: string | null   (deep link a Google Maps)      │
│  source: string            ("google_places" | "local")    │
│  confidence: float | null  (0-1, relevancia del match)    │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Modelo Pydantic Propuesto

Ubicación: `application/models/responses.py`

```python
class Recommendation(BaseModel):
    """Single recommendation card: venue + accessibility + routes."""

    id: str
    name: str
    type: str = "venue"
    summary: Optional[str] = None

    venue: Optional[Venue] = None
    accessibility: Optional[Accessibility] = None
    routes: list[Route] = Field(default_factory=list)

    maps_url: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
```

Y extender `ChatResponse`:

```python
class ChatResponse(BaseResponse):
    ai_response: str
    session_id: Optional[str] = None
    processing_time: Optional[float] = None

    recommendations: list[Recommendation] = Field(default_factory=list)  # ← NUEVO

    tourism_data: Optional[TourismData] = None  # ← mantener deprecated
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    pipeline_steps: Optional[list[PipelineStep]] = None
    metadata: Optional[Dict[str, Any]] = None
```

### 2.3 JSON de Respuesta Ideal (Multi-Recomendación)

```json
{
  "status": "success",
  "ai_response": "He encontrado 3 restaurantes accesibles cerca de tu ubicación...",
  "recommendations": [
    {
      "id": "ChIJ_abc123",
      "name": "Restaurante La Barraca",
      "type": "restaurant",
      "summary": "Paella valenciana, acceso completo en silla de ruedas",
      "venue": {
        "name": "Restaurante La Barraca",
        "type": "restaurant",
        "accessibility_score": 9.0,
        "facilities": ["wheelchair_ramps", "adapted_bathrooms", "elevator_access"],
        "certification": "iso_21542",
        "opening_hours": { "lunes_a_sabado": "13:00-23:00", "domingo": "13:00-16:00" },
        "pricing": { "menu_del_dia": "18 EUR", "carta": "25-40 EUR" },
        "rating": 4.5,
        "total_reviews": 1240
      },
      "accessibility": {
        "level": "fully_accessible",
        "score": 9.0,
        "facilities": ["wheelchair_ramps", "adapted_bathrooms"],
        "certification": "iso_21542",
        "wheelchair_accessible_entrance": true,
        "wheelchair_accessible_restroom": true,
        "wheelchair_accessible_seating": true,
        "warnings": []
      },
      "routes": [
        {
          "transport": "metro",
          "line": "L1 Banco de España",
          "duration": "12 min",
          "accessibility": "full",
          "cost": "1.50 EUR",
          "steps": [
            "Tomar L1 dirección Pinar de Chamartín",
            "Bajar en Banco de España",
            "Salir por ascensor accesible, 3 min andando"
          ]
        }
      ],
      "maps_url": "https://www.google.com/maps/place/?q=place_id:ChIJ_abc123",
      "source": "google_places",
      "confidence": 0.92
    },
    {
      "id": "ChIJ_def456",
      "name": "Taberna Los Galayos",
      "type": "restaurant",
      "summary": "Cocina castellana tradicional, acceso parcial",
      "venue": {
        "name": "Taberna Los Galayos",
        "type": "restaurant",
        "accessibility_score": 6.5,
        "facilities": ["adapted_bathrooms"],
        "rating": 4.2,
        "total_reviews": 890
      },
      "accessibility": {
        "level": "partially_accessible",
        "score": 6.5,
        "facilities": ["adapted_bathrooms"],
        "warnings": ["Entrada principal con escalón de 5cm"]
      },
      "routes": [],
      "maps_url": "https://www.google.com/maps/place/?q=place_id:ChIJ_def456",
      "source": "google_places",
      "confidence": 0.85
    },
    {
      "id": "local_001",
      "name": "100 Montaditos Gran Vía",
      "type": "restaurant",
      "summary": "Cadena económica con accesibilidad completa",
      "venue": {
        "name": "100 Montaditos Gran Vía",
        "type": "restaurant",
        "accessibility_score": 8.0,
        "facilities": ["wheelchair_ramps"],
        "pricing": { "bocadillo": "1-2.50 EUR" }
      },
      "accessibility": {
        "level": "fully_accessible",
        "score": 8.0,
        "warnings": []
      },
      "routes": [],
      "maps_url": null,
      "source": "local",
      "confidence": 0.70
    }
  ],
  "tourism_data": null,
  "intent": "restaurant_search",
  "entities": {
    "location": "Madrid centro",
    "accessibility_requirement": "wheelchair",
    "location_ner": {
      "status": "ok",
      "locations": ["Madrid"],
      "top_location": "Madrid centro"
    }
  },
  "pipeline_steps": [
    { "name": "NLU", "tool": "tourism_nlu", "status": "completed", "duration_ms": 125 },
    { "name": "LocationNER", "tool": "location_ner", "status": "completed", "duration_ms": 95 },
    { "name": "PlacesSearch", "tool": "places_search", "status": "completed", "duration_ms": 340 },
    { "name": "AccessibilityEnrichment", "tool": "accessibility_enrichment", "status": "completed", "duration_ms": 210 },
    { "name": "Directions", "tool": "directions", "status": "completed", "duration_ms": 180 }
  ],
  "metadata": {
    "timestamp": "2026-03-12T10:30:00",
    "session_type": "production",
    "language": "es-ES",
    "tool_outputs": {
      "nlu": {
        "status": "ok",
        "intent": "restaurant_search",
        "confidence": 0.87,
        "entities": { "destination": "restaurante", "accessibility": "wheelchair" },
        "provider": "openai"
      },
      "location_ner": {
        "status": "ok",
        "locations": ["Madrid"],
        "top_location": "Madrid centro",
        "provider": "spacy"
      },
      "places": {
        "candidates_count": 3,
        "provider": "google_places",
        "query": "restaurante accesible Madrid centro"
      },
      "accessibility": {
        "enriched_count": 3,
        "provider": "overpass"
      },
      "directions": {
        "routes_computed": 1,
        "provider": "google_routes",
        "note": "Solo top-1 por coste API"
      }
    }
  }
}
```

### 2.4 Regla de Transformación: `ToolPipelineContext` → `Recommendation[]`

```
ToolPipelineContext.places[]             ──┐
ToolPipelineContext.accessibility_map{}  ──┼──→  Recommendation[]
ToolPipelineContext.routes_map{}         ──┘

Para cada PlaceCandidate en ctx.places:
  rec.id             = place.place_id or uuid4()
  rec.name           = place.name
  rec.type           = place.types[0] if place.types else "venue"
  rec.venue          = merge(place fields, venue_detail if place_id matches)
  rec.accessibility  = ctx.accessibility_map.get(place.place_id)
  rec.routes         = ctx.routes_map.get(place.place_id, [])
  rec.maps_url       = build_maps_url(place.place_id, place.latitude, place.longitude)
  rec.confidence     = place.rating / 5.0  (normalizado a 0-1)
  rec.source         = place.source
```

### 2.5 Backward Compatibility con `tourism_data`

Durante la migración, el sistema mantiene ambos campos:

```python
# En backend_adapter.py — durante transición
structured_response["recommendations"] = recommendations  # NUEVO
structured_response["tourism_data"] = (
    recommendations[0].to_tourism_data() if recommendations else None
)  # DEPRECATED — convierte top-1 al formato legacy
```

Esto permite que:
- UIs nuevas consuman `recommendations[]`
- UIs existentes sigan funcionando con `tourism_data` (sin cambios)
- Se pueda eliminar `tourism_data` en una fase posterior

---

## 3. Arquitectura Recomendada

### 3.1 Diagrama de Flujo Propuesto

```
┌──────────────────────────────────────────────────────────────────┐
│                     AGENTES (Business Layer)                      │
│                                                                    │
│  NLU + NER (paralelo)                                             │
│      ↓                                                             │
│  PlacesSearch ──→ N PlaceCandidate[]              ← CAMBIO        │
│      ↓                                                             │
│  AccessibilityEnrichment ──→ por cada place       ← CAMBIO        │
│      ↓                                                             │
│  Directions ──→ solo top-1 (por coste API)                        │
│      ↓                                                             │
│  ToolPipelineContext (acumulador multi-place)      ← CAMBIO        │
│      ↓                                                             │
│  LLM genera ai_response (texto conversacional)                    │
│      ↓                                                             │
│  AgentResponse(response_text, tool_results, metadata)             │
└──────────────────────┬────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  ADAPTER (Application Layer)                       │
│                                                                    │
│  ResponseTransformer.transform(pipeline_ctx)      ← NUEVO         │
│    - Mapea PlaceCandidate[] → Recommendation[]                    │
│    - Enriquece con accessibility, routes, maps_url                │
│    - Ordena por relevancia + accesibilidad + perfil               │
│    - Valida con Pydantic Recommendation model                     │
│    - Genera tourism_data legacy para backward compat              │
│                                                                    │
│  backend_adapter.py                                                │
│    - Invoca ResponseTransformer                                    │
│    - Construye ChatResponse con recommendations[]                 │
└──────────────────────┬────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                      UI (Presentation Layer)                       │
│                                                                    │
│  CardRenderer.renderRecommendations(recommendations)  ← CAMBIO    │
│    - 1 card por Recommendation                                    │
│    - Campos opcionales con graceful degradation                   │
│    - Link a Google Maps si maps_url presente                      │
│    - Warnings de accesibilidad visibles                           │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Responsabilidades por Capa

| Capa | Archivo(s) | Responsabilidad | Cambios |
|------|-----------|-----------------|---------|
| **Business** | `shared/models/tool_models.py` | Modelos tipados del pipeline | Añadir `places[]`, `accessibility_map`, `routes_map` |
| **Business** | `business/domains/tourism/tools/places_search_tool.py` | Búsqueda de lugares | Devolver top-N candidatos |
| **Business** | `business/domains/tourism/tools/accessibility_enrichment_tool.py` | Enriquecimiento accesibilidad | Procesar cada place en `places[]` |
| **Business** | `business/domains/tourism/tools/directions_tool.py` | Cálculo de rutas | Rutas solo para top-1 (por coste) |
| **Business** | `business/domains/tourism/agent.py` | Orquestación pipeline | Adaptar a multi-place pipeline |
| **Application** | `application/orchestration/response_transformer.py` | **NUEVO** — Transformación | `ToolPipelineContext → Recommendation[]` |
| **Application** | `application/models/responses.py` | Modelos de respuesta API | Añadir `Recommendation`, extender `ChatResponse` |
| **Application** | `application/orchestration/backend_adapter.py` | Adaptador backend | Integrar `ResponseTransformer` |
| **Presentation** | `presentation/static/js/cards.js` | Renderizado de tarjetas | Nuevo `renderRecommendations()` |
| **Presentation** | `presentation/static/js/chat.js` | Gestión de chat | Priorizar `recommendations` sobre `tourism_data` |

### 3.3 Principio de Desacoplamiento

```
Agente  ──produces──→  ToolPipelineContext (typed, internal contract)
                              │
                       ResponseTransformer (boundary)
                              │
API     ──serves────→  Recommendation[] (stable external contract, versioned)
                              │
UI      ──consumes──→  CardRenderer (presentation only, no business logic)
```

**Regla:** La UI **nunca** accede a `metadata.tool_outputs` para renderizar cards. `recommendations[]` es el contrato estable y único punto de consumo.

### 3.4 Dónde Ocurre la Transformación

**Decisión: en el Application Layer (`ResponseTransformer`), NO en el agente ni en la UI.**

| Alternativa | Descartada por |
|-------------|----------------|
| En el agente (business layer) | El agente no debe conocer el contrato de la API REST. Viola separación de capas. |
| En la UI (presentation layer) | La UI no debe hacer lógica de merge/ranking/filtrado. Imposible testear. |
| En el adapter directamente | El adapter ya es complejo (~500 líneas). Extraer a clase dedicada es más mantenible. |

**`ResponseTransformer` es una clase pura (sin side effects) fácilmente testeable.**

---

## 4. Diseño de la Representación en UI

### 4.1 Campos por Sección de Card

Cada `Recommendation` se renderiza como una card con secciones condicionales:

```
┌─────────────────────────────────────────────────────┐
│  HEADER: name, type icon, accessibility gauge       │
│─────────────────────────────────────────────────────│
│  VENUE SECTION (si venue presente):                 │
│    - Facilities badges                              │
│    - Certification badge                            │
│    - Opening hours                                  │
│    - Pricing                                        │
│    - Google rating + reviews count                  │
│─────────────────────────────────────────────────────│
│  ACCESSIBILITY SECTION (si accessibility presente): │
│    - Level badge (fully/partially/not)              │
│    - Score bar                                      │
│    - Warnings (⚠️ alertas visibles)                 │
│─────────────────────────────────────────────────────│
│  ROUTES SECTION (si routes no vacío):               │
│    - Transport icon + line + duration               │
│    - Accessibility status                           │
│    - Cost                                           │
│    - Steps (expandible)                             │
│─────────────────────────────────────────────────────│
│  FOOTER: Google Maps link (si maps_url presente)    │
└─────────────────────────────────────────────────────┘
```

### 4.2 Manejo de Información Opcional (Graceful Degradation)

| Campo | Requerido | Fallback si Ausente |
|-------|-----------|---------------------|
| `name` | Sí | `"Recomendación"` |
| `type` | Sí | `"venue"` (icono genérico) |
| `summary` | No | No mostrar subtítulo |
| `venue` | No | No mostrar sección venue |
| `venue.accessibility_score` | No | No mostrar gauge |
| `venue.facilities` | No | Sección vacía |
| `venue.opening_hours` | No | No mostrar horarios |
| `venue.pricing` | No | No mostrar precios |
| `venue.rating` | No | No mostrar estrellas |
| `accessibility` | No | No mostrar sección |
| `accessibility.level` | No | No mostrar badge |
| `accessibility.warnings` | No | No mostrar alertas |
| `routes` | No (array vacío) | No mostrar sección rutas |
| `maps_url` | No | No mostrar botón Maps |

### 4.3 Estructura del CardRenderer Actualizado

```javascript
class CardRenderer {
    /**
     * Entry point: prioriza recommendations[] sobre tourism_data legacy.
     */
    static render(data) {
        if (data.recommendations && data.recommendations.length > 0) {
            return CardRenderer.renderRecommendations(data.recommendations);
        }
        // Fallback legacy
        if (data.tourismData) {
            return CardRenderer.renderLegacy(data.tourismData);
        }
        return '';
    }

    static renderRecommendations(recommendations) {
        return '<div class="recommendations-grid mt-3">'
            + recommendations.map(rec => CardRenderer.renderRecommendationCard(rec)).join('')
            + '</div>';
    }

    static renderRecommendationCard(rec) {
        return `
            <div class="card recommendation-card mb-3">
                <div class="card-body p-3">
                    ${CardRenderer.renderCardHeader(rec)}
                    ${rec.summary ? `<p class="text-muted small mb-2">${CardRenderer.escapeHtml(rec.summary)}</p>` : ''}
                    ${rec.venue ? CardRenderer.renderVenueSection(rec.venue) : ''}
                    ${rec.accessibility ? CardRenderer.renderAccessibilitySection(rec.accessibility) : ''}
                    ${rec.routes && rec.routes.length > 0 ? CardRenderer.renderRoutesSection(rec.routes) : ''}
                    ${rec.maps_url ? CardRenderer.renderMapsLink(rec.maps_url, rec.name) : ''}
                </div>
            </div>
        `;
    }

    static renderCardHeader(rec) { /* name + type icon + gauge */ }
    static renderVenueSection(venue) { /* facilities, hours, pricing, rating */ }
    static renderAccessibilitySection(acc) { /* level, score, warnings */ }
    static renderRoutesSection(routes) { /* transport, duration, steps */ }
    static renderMapsLink(url, name) { /* Google Maps button */ }
}
```

### 4.4 Iconos por Tipo de Recomendación

```javascript
static TYPE_ICONS = {
    'restaurant': 'bi-cup-straw',
    'museum': 'bi-building',
    'park': 'bi-tree',
    'hotel': 'bi-house-door',
    'theater': 'bi-music-note-beamed',
    'monument': 'bi-geo-alt',
    'shopping': 'bi-bag',
    'default': 'bi-pin-map',
};
```

---

## 5. Plan de Migración

### Visión General de Fases

```
Fase A (Backend Models)     Fase B (Transformer)       Fase C (UI)           Fase D (Consolidación)
┌──────────────────┐       ┌──────────────────┐       ┌──────────────┐       ┌──────────────────┐
│ Multi-place en   │       │ Response         │       │ Card per     │       │ Deprecar         │
│ ToolPipeline     │──→    │ Transformer      │──→    │ Recommen-    │──→    │ tourism_data     │
│ Context          │       │ + Pydantic model │       │ dation       │       │ + Tests + Docs   │
└──────────────────┘       └──────────────────┘       └──────────────┘       └──────────────────┘
```

### Fase A: Multi-Place en Pipeline (Business Layer)

**Objetivo:** Que el pipeline transporte N candidatos en vez de 1.

#### A.1 Extender `ToolPipelineContext`

**Archivo:** `shared/models/tool_models.py`

```python
class ToolPipelineContext(BaseModel):
    # ... campos existentes sin cambio ...
    place: Optional[PlaceCandidate] = None          # mantener (backward compat)
    accessibility: Optional[AccessibilityInfo] = None  # mantener
    routes: list[RouteOption] = []                   # mantener
    venue_detail: Optional[VenueDetail] = None       # mantener

    # NUEVOS campos multi-place
    places: list[PlaceCandidate] = Field(default_factory=list)
    accessibility_map: dict[str, AccessibilityInfo] = Field(default_factory=dict)
    routes_map: dict[str, list[RouteOption]] = Field(default_factory=dict)
```

**Nota:** Los campos singulares (`place`, `accessibility`, `routes`) se mantienen para que las tools legacy y el prompt builder sigan funcionando sin cambios.

#### A.2 Modificar `PlacesSearchTool`

**Archivo:** `business/domains/tourism/tools/places_search_tool.py`

Cambio: buscar top-3 en vez de top-1.

```python
async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
    # ... búsqueda existente ...
    candidates = await self._service.search_places(query, limit=3)  # ← CAMBIO: limit=3

    if candidates:
        ctx.place = candidates[0]          # backward compat (top-1)
        ctx.places = candidates            # NUEVO: todos los candidatos
    return ctx
```

#### A.3 Modificar `AccessibilityEnrichmentTool`

**Archivo:** `business/domains/tourism/tools/accessibility_enrichment_tool.py`

Cambio: enriquecer cada place en `places[]`.

```python
async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
    # Mantener lógica existente para ctx.place (backward compat)
    if ctx.place:
        ctx.accessibility = await self._enrich_single(ctx.place)

    # NUEVO: enriquecer todos los candidatos
    for place in ctx.places:
        if place.place_id:
            info = await self._enrich_single(place)
            ctx.accessibility_map[place.place_id] = info

    return ctx
```

#### A.4 Modificar `DirectionsTool`

**Archivo:** `business/domains/tourism/tools/directions_tool.py`

Cambio: calcular rutas solo para top-1 (por coste API) y almacenar en `routes_map`.

```python
async def execute(self, ctx: ToolPipelineContext) -> ToolPipelineContext:
    # Mantener lógica existente para ctx.routes (backward compat)
    # ...

    # NUEVO: mapear rutas al place correspondiente
    if ctx.place and ctx.place.place_id:
        ctx.routes_map[ctx.place.place_id] = ctx.routes

    return ctx
```

#### A.5 Adaptar `TourismMultiAgent._execute_pipeline_async()`

**Archivo:** `business/domains/tourism/agent.py`

Cambio mínimo: propagar los nuevos campos en metadata para que el adapter pueda acceder al pipeline context completo.

```python
# En _build_metadata() o al final de _execute_pipeline_async():
metadata["pipeline_context"] = {
    "places": [p.model_dump() for p in ctx.places],
    "accessibility_map": {k: v.model_dump() for k, v in ctx.accessibility_map.items()},
    "routes_map": {k: [r.model_dump() for r in rs] for k, rs in ctx.routes_map.items()},
}
```

### Fase B: Capa de Transformación (Application Layer)

**Objetivo:** Nuevo `ResponseTransformer` que produzca `Recommendation[]`.

#### B.1 Crear `ResponseTransformer`

**Archivo nuevo:** `application/orchestration/response_transformer.py`

```python
"""Transforms pipeline tool outputs into UI-consumable Recommendation list."""

from typing import Any, Optional
from uuid import uuid4

from application.models.responses import Recommendation, Venue, Accessibility, Route


class ResponseTransformer:
    """Pure transformation: ToolPipelineContext data → Recommendation[]."""

    @staticmethod
    def transform(
        pipeline_data: dict[str, Any],
        profile_context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Transform pipeline_context from metadata into Recommendation dicts.

        Args:
            pipeline_data: metadata["pipeline_context"] from AgentResponse
            profile_context: optional profile for ranking bias

        Returns:
            List of Recommendation-compatible dicts, ordered by relevance.
        """
        places = pipeline_data.get("places", [])
        acc_map = pipeline_data.get("accessibility_map", {})
        routes_map = pipeline_data.get("routes_map", {})

        recommendations = []
        for place in places:
            place_id = place.get("place_id") or str(uuid4())

            rec = {
                "id": place_id,
                "name": place.get("name", "Recomendación"),
                "type": (place.get("types") or ["venue"])[0],
                "summary": None,
                "venue": ResponseTransformer._build_venue(place),
                "accessibility": acc_map.get(place_id),
                "routes": routes_map.get(place_id, []),
                "maps_url": ResponseTransformer._build_maps_url(place),
                "source": place.get("source"),
                "confidence": ResponseTransformer._normalize_confidence(place),
            }
            recommendations.append(rec)

        # Sort by accessibility score descending, then confidence
        recommendations.sort(
            key=lambda r: (
                (r.get("accessibility") or {}).get("score") or 0,
                r.get("confidence") or 0,
            ),
            reverse=True,
        )

        return recommendations

    @staticmethod
    def _build_venue(place: dict) -> dict:
        return {
            "name": place.get("name"),
            "type": (place.get("types") or ["venue"])[0],
            "accessibility_score": place.get("rating"),
            "facilities": [],
            "rating": place.get("rating"),
            "total_reviews": place.get("total_reviews"),
        }

    @staticmethod
    def _build_maps_url(place: dict) -> Optional[str]:
        place_id = place.get("place_id")
        if place_id:
            return f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        lat = place.get("latitude")
        lng = place.get("longitude")
        if lat and lng:
            return f"https://www.google.com/maps/@{lat},{lng},17z"
        return None

    @staticmethod
    def _normalize_confidence(place: dict) -> Optional[float]:
        rating = place.get("rating")
        if rating is not None:
            return min(rating / 5.0, 1.0)
        return None
```

#### B.2 Crear modelo `Recommendation` en Pydantic

**Archivo:** `application/models/responses.py` (añadir al existente)

```python
class Recommendation(BaseModel):
    """A single recommendation card combining venue + accessibility + routes."""

    id: str
    name: str
    type: str = "venue"
    summary: Optional[str] = None

    venue: Optional[Venue] = None
    accessibility: Optional[Accessibility] = None
    routes: list[Route] = Field(default_factory=list)

    maps_url: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
```

#### B.3 Integrar en `backend_adapter.py`

En `process_query()`, tras obtener `raw_metadata` del agente:

```python
from application.orchestration.response_transformer import ResponseTransformer

# Después de obtener raw_metadata...
pipeline_context_data = raw_metadata.get("pipeline_context", {})
recommendations = []
if pipeline_context_data and pipeline_context_data.get("places"):
    recommendations = ResponseTransformer.transform(
        pipeline_context_data, profile_context=profile_context
    )

structured_response["recommendations"] = recommendations

# Backward compat: mantener tourism_data del top-1
# (se puede eliminar en Fase D)
```

### Fase C: Actualización de UI (Presentation Layer)

**Objetivo:** Cards que rendericen `recommendations[]`.

#### C.1 Actualizar `CardRenderer`

**Archivo:** `presentation/static/js/cards.js`

- Añadir `renderRecommendations(recommendations)` como nuevo entry point
- Añadir `renderRecommendationCard(rec)` que compone las secciones
- Añadir `renderMapsLink(url, name)` para el botón de Google Maps
- Añadir `renderWarnings(warnings)` para alertas de accesibilidad
- Mantener métodos existentes como fallback legacy

#### C.2 Actualizar `ChatHandler`

**Archivo:** `presentation/static/js/chat.js`

En el método `addMessage()`, priorizar `recommendations` sobre `tourism_data`:

```javascript
// Al renderizar la respuesta del asistente:
let cardsHtml = '';
if (response.recommendations && response.recommendations.length > 0) {
    cardsHtml = CardRenderer.renderRecommendations(response.recommendations);
} else if (response.tourism_data) {
    cardsHtml = CardRenderer.render(response.tourism_data);  // legacy fallback
}
```

### Fase D: Consolidación

#### D.1 Tests para `ResponseTransformer`

**Archivo nuevo:** `tests/test_application/test_response_transformer.py`

Casos de test mínimos:
- `test_transform_empty_places` → devuelve `[]`
- `test_transform_single_place` → devuelve 1 recommendation con venue
- `test_transform_multi_place` → devuelve N recommendations ordenados
- `test_transform_with_accessibility_map` → accessibility se mapea correctamente
- `test_transform_with_routes_map` → routes se mapea solo al place correspondiente
- `test_build_maps_url_with_place_id` → URL con place_id
- `test_build_maps_url_with_coords` → URL con lat/lng fallback
- `test_build_maps_url_none` → None si no hay datos
- `test_backward_compat_tourism_data` → `tourism_data` sigue siendo válido

#### D.2 Deprecar `tourism_data`

- Marcar `tourism_data` como deprecated en `API_REFERENCE.md`
- Log warning si la UI accede a `tourism_data` en vez de `recommendations`
- Planificar eliminación para versión 3.0

#### D.3 Actualizar Documentación

- `API_REFERENCE.md`: documentar `recommendations[]` en response de `POST /api/v1/chat/message`
- `ESTADO_ACTUAL_SISTEMA.md`: actualizar sección 4 (contrato de salida)
- `ROADMAP.md`: marcar esta fase como completada

#### D.4 Actualizar `metadata.tool_outputs`

Extender `tool_outputs` para incluir resumen de tools de dominio:

```python
stable_tool_outputs["places"] = {
    "candidates_count": len(ctx.places),
    "provider": places_service_provider,
}
stable_tool_outputs["accessibility"] = {
    "enriched_count": len(ctx.accessibility_map),
    "provider": accessibility_service_provider,
}
stable_tool_outputs["directions"] = {
    "routes_computed": sum(len(rs) for rs in ctx.routes_map.values()),
    "provider": directions_service_provider,
}
```

---

## 6. Ejemplo Completo

### 6.1 Respuesta Actual del Sistema (Simplificada)

```json
{
  "status": "success",
  "ai_response": "He encontrado que el Restaurante La Barraca es una excelente opción accesible...",
  "tourism_data": {
    "venue": {
      "name": "Restaurante La Barraca",
      "type": "restaurant",
      "accessibility_score": 9.0,
      "facilities": ["wheelchair_ramps", "adapted_bathrooms"]
    },
    "accessibility": {
      "level": "fully_accessible",
      "score": 9.0,
      "certification": "iso_21542"
    },
    "routes": [
      { "transport": "metro", "line": "L1", "duration": "12 min", "accessibility": "full" }
    ]
  },
  "metadata": {
    "tool_outputs": {
      "nlu": { "intent": "restaurant_search", "confidence": 0.87 },
      "location_ner": { "top_location": "Madrid" }
    }
  }
}
```

**Problema:** Solo 1 restaurante en `tourism_data`. El LLM menciona 3 en `ai_response`, pero los datos estructurados solo tienen 1.

### 6.2 Respuesta Transformada (Post-Migración)

Ver sección [2.3](#23-json-de-respuesta-ideal-multi-recomendación) para el JSON completo.

**Mejoras:**
- 3 recomendaciones con datos estructurados independientes
- Cada una con su accesibilidad, rutas y link a Maps
- Warnings visibles ("Escalón de 5cm")
- Ordenadas por score de accesibilidad
- Backward compat con `tourism_data: null`

### 6.3 Representación Visual de las Tarjetas

```
┌──────────────────────────────────────────────────────────┐
│  🍽️ Restaurante La Barraca                    [9.0/10]  │
│  Paella valenciana, acceso completo en silla de ruedas   │
│                                                           │
│  🦽 Rampas   🚿 Aseos adaptados   🛗 Ascensor          │
│  📜 ISO 21542                                            │
│  ⏰ L-S: 13:00-23:00  |  Dom: 13:00-16:00               │
│  💰 Menú: 18 EUR  |  Carta: 25-40 EUR                   │
│  ⭐ 4.5 (1240 reseñas)                                  │
│                                                           │
│  ♿ Accesibilidad: Completa                               │
│  ████████████████████░░ 9.0/10                           │
│                                                           │
│  🚇 Metro L1 Banco de España · 12 min · ♿ Completo     │
│     1. Tomar L1 dirección Pinar de Chamartín             │
│     2. Bajar en Banco de España                           │
│     3. Salir por ascensor, 3 min andando                  │
│                                                           │
│  [📍 Ver en Google Maps]                                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  🍽️ Taberna Los Galayos                       [6.5/10]  │
│  Cocina castellana tradicional, acceso parcial            │
│                                                           │
│  🚿 Aseos adaptados                                     │
│  ⭐ 4.2 (890 reseñas)                                   │
│                                                           │
│  ♿ Accesibilidad: Parcial                                │
│  █████████████░░░░░░░░░ 6.5/10                           │
│  ⚠️ Entrada principal con escalón de 5cm                 │
│                                                           │
│  [📍 Ver en Google Maps]                                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  🍽️ 100 Montaditos Gran Vía                   [8.0/10]  │
│  Cadena económica con accesibilidad completa              │
│                                                           │
│  🦽 Rampas                                               │
│  💰 Bocadillo: 1-2.50 EUR                               │
│                                                           │
│  ♿ Accesibilidad: Completa                               │
│  ████████████████░░░░░░ 8.0/10                           │
└──────────────────────────────────────────────────────────┘
```

**Notas sobre la representación:**
- La segunda tarjeta NO tiene rutas → esa sección simplemente no aparece
- La segunda tarjeta SÍ tiene warning → se muestra destacado con ⚠️
- La tercera tarjeta NO tiene `maps_url` → botón de Maps no aparece
- La tercera tarjeta NO tiene horarios → sección omitida
- Cada tarjeta se adapta a la información disponible (graceful degradation)

---

## 7. Checklist de Implementación

### Fase A: Backend Models
- [ ] Extender `ToolPipelineContext` con `places[]`, `accessibility_map{}`, `routes_map{}`
- [ ] Modificar `PlacesSearchTool` para devolver top-3
- [ ] Modificar `AccessibilityEnrichmentTool` para enriquecer cada place
- [ ] Modificar `DirectionsTool` para mapear rutas por place_id
- [ ] Adaptar `TourismMultiAgent` para propagar `pipeline_context` en metadata
- [ ] Verificar que pipeline legacy (singular) sigue funcionando (backward compat)

### Fase B: Transformer
- [ ] Crear `application/orchestration/response_transformer.py`
- [ ] Crear modelo Pydantic `Recommendation` en `responses.py`
- [ ] Extender `ChatResponse` con campo `recommendations`
- [ ] Integrar `ResponseTransformer` en `backend_adapter.py`
- [ ] Verificar backward compat: `tourism_data` sigue poblándose

### Fase C: UI
- [ ] Añadir `renderRecommendations()` en `cards.js`
- [ ] Añadir `renderRecommendationCard()` con secciones condicionales
- [ ] Añadir `renderMapsLink()` para botón Google Maps
- [ ] Añadir `renderWarnings()` para alertas de accesibilidad
- [ ] Actualizar `chat.js` para priorizar `recommendations` sobre `tourism_data`
- [ ] Añadir CSS para `.recommendation-card`, `.warning-badge`, `.maps-link`
- [ ] Añadir `TYPE_ICONS` mapping por tipo de recomendación
- [ ] Test manual: verificar graceful degradation con campos faltantes

### Fase D: Consolidación
- [ ] Escribir tests para `ResponseTransformer` (mínimo 8 casos)
- [ ] Extender `metadata.tool_outputs` con resumen de places/accessibility/directions
- [ ] Marcar `tourism_data` como deprecated en `API_REFERENCE.md`
- [ ] Actualizar `ESTADO_ACTUAL_SISTEMA.md`
- [ ] Actualizar `ROADMAP.md`
- [ ] Verificar que todos los tests existentes (156) siguen pasando

---

## Decisiones Arquitectónicas Resumidas

| # | Decisión | Elegida | Alternativa Descartada | Razón |
|---|----------|---------|------------------------|-------|
| 1 | Dónde transformar datos | Application Layer (`ResponseTransformer`) | En agente / En UI | Separación de concerns; testeable; no acopla agente con API ni UI con negocio |
| 2 | Modelo multi-recomendación | `recommendations[]` en root del response | Extender `tourism_data.venues[]` | Contrato nuevo limpio; sin ambigüedad singular/plural; no rompe legacy |
| 3 | Rutas por recomendación | Solo top-1 place con rutas calculadas | Rutas para todos los candidatos | Balance coste API / UX; expandible bajo demanda |
| 4 | Backward compatibility | Mantener `tourism_data` (deprecated, puede ser null) | Eliminar inmediatamente | Migración gradual; no rompe UI existente |
| 5 | Maps URL | Generar en transformer (backend) | Generar en frontend | El frontend no debe conocer lógica de construcción de URLs de Google |
| 6 | Ordering de recommendations | Por accessibility score desc, luego confidence | Por confidence solamente | El producto es turismo accesible; score de accesibilidad es la métrica principal |
| 7 | Límite de candidatos | Top-3 por defecto | Configurable vía request | Simple para POC→prod; configurable después si necesario |

---

**Siguiente paso:** Revisión de este documento por el equipo antes de iniciar implementación.
