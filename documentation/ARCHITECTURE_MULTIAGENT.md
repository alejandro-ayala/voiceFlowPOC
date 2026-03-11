# Arquitectura Multi-Agente: LangChain + STT

**Actualizado**: 11 de Marzo de 2026
**Version**: 5.1 - Fase 0 (Contratos) + Fase 1 (API-First Tools) completadas + auditoría documental

---

## ✅ ESTADO ACTUAL: Pipeline completo con Tools API-First (Post Fase 0 + Fase 1)

**El pipeline integra NLU, NER y tools de dominio reales:**
- ✅ **NLU Tool**: proveedor configurable (`openai` principal, `keyword` fallback) con shadow mode
- ✅ **LocationNER Tool**: extracción real de localizaciones con spaCy
- ✅ **PlacesSearchTool**: Google Places API (New) v1 con fallback a datos mock
- ✅ **DirectionsTool**: Google Routes v2 + OpenRouteService con fallback a datos mock
- ✅ **AccessibilityEnrichmentTool**: Overpass/OSM con fallback a datos mock
- ⚠️ **Legacy Tools**: AccessibilityAnalysisTool, RoutePlanningTool, TourismInfoTool (backward compat, usadas solo si no se inyectan servicios Phase 1)

**Stack API-First:**
- Selección de proveedor via `.env`: `VOICEFLOW_PLACES_PROVIDER=local|google`, etc.
- Con `local` (default): fallback automático a datos mock, sin errores
- Con API keys configuradas: datos estructurados reales de cualquier ciudad
- Capa de resiliencia: circuit breaker + rate limiter + budget tracker

**Pipeline tipado:** `ToolPipelineContext` (Pydantic) fluye entre todas las tools con contratos estables.

**Pendiente:** Routing por intent (actualmente se ejecutan todas las tools siempre). Ver [ESTADO_ACTUAL_SISTEMA.md](./ESTADO_ACTUAL_SISTEMA.md).

---

## Contexto

El sistema VoiceFlow Tourism PoC combina Speech-to-Text (STT) con un sistema multi-agente LangChain para proporcionar asistencia de turismo accesible en Madrid. El usuario habla en español, el sistema transcribe y procesa la consulta a través de agentes especializados que generan recomendaciones de accesibilidad.

## Flujo de datos

```
 Usuario (voz en espanol)
         |
         v
  +-----------------+     Presentation Layer
  | Browser (UI)    |     presentation/templates/index.html
  | AudioHandler.js |     presentation/static/js/audio.js
  +-----------------+
         |
         | POST /api/v1/audio/transcribe (WebM audio)
         v
  +-------------------+   Application Layer
  | audio.py endpoint |   application/api/v1/audio.py
  +-------------------+
         |
         | Depends(get_audio_processor)
         v
  +-------------------+   Application Layer
  | AudioService      |   application/services/audio_service.py
  +-------------------+
         |
         | _get_stt_agent() -> lazy init
         v
  +-------------------+   Integration Layer
  | VoiceflowSTTAgent |   integration/external_apis/stt_agent.py
  +-------------------+
         |
         | STTServiceFactory.create_from_config()
         v
  +-------------------+   Integration Layer
  | STTServiceFactory |   integration/external_apis/stt_factory.py
  +---------+---------+
            |
    +-------+-------+-------+
    |               |               |
    v               v               v
 Azure STT    Whisper Local   Whisper API
 (produccion) (offline)       (cloud)

         === Transcripcion completada ===

         | Texto transcrito
         v
  +-------------------+   Presentation Layer (UI)
  | ChatHandler.js    |   El usuario puede editar o enviar directamente
  +-------------------+
         |
         | POST /api/v1/chat/message
         v
  +-------------------+   Application Layer
  | chat.py endpoint  |   application/api/v1/chat.py
  +-------------------+
         |
         | Depends(get_backend_adapter)
         v
  +----------------------+   Application Layer
  | LocalBackendAdapter  |   application/orchestration/backend_adapter.py
  +----------------------+
         |
         | use_real_agents?
         |
    +----+----+
    |         |
    v         v
  REAL      SIMULADO
    |         |
    v         |
  +----------------------------------+   Business Layer (core/)
  | MultiAgentOrchestrator           |   business/core/orchestrator.py
  |   process_request() → AgentResponse
  +----------------------------------+
    |
    v (Template Method)
  +----------------------------------+   Business Layer (domains/tourism/)
  | TourismMultiAgent                |   business/domains/tourism/agent.py
  |   _execute_pipeline()            |
  +----------------------------------+
    |
       | Ejecuta pipeline de tools (NLU+NER en paralelo, dominio en secuencia)
    |
    +---> TourismNLUTool             (tools/nlu_tool.py)          ── Foundation
       +---> LocationNERTool            (tools/location_ner_tool.py)  ── Foundation
    +---> PlacesSearchTool           (tools/places_search_tool.py)  ── Phase 1 (Google Places / Local)
    +---> AccessibilityEnrichmentTool (tools/accessibility_enrichment_tool.py) ── Phase 1 (Overpass / Local)
    +---> DirectionsTool             (tools/directions_tool.py)    ── Phase 1 (Google Routes+ORS / Local)
    |
    | _build_response_prompt()       (prompts/response_prompt.py)
    v
  +-------------------+
  | ChatOpenAI GPT-4  |   Genera respuesta conversacional en espanol
  +-------------------+
         |
         v
  Respuesta JSON al frontend
```

## Componentes del sistema multi-agente

### Orquestador: `TourismMultiAgent`

**Ubicacion**: `business/domains/tourism/agent.py`
**Hereda de**: `business/core/orchestrator.py` → `MultiAgentOrchestrator`
**LLM**: ChatOpenAI GPT-4 (temperature=0.3, max_tokens=2500)

El orquestador extiende `MultiAgentOrchestrator` (patron Template Method) e implementa `_execute_pipeline()` con NLU y NER en paralelo (`asyncio.gather`), seguido de `EntityResolver` para merge de outputs, y luego el resto de tools en secuencia. El algoritmo base (invoke LLM, gestionar historial, retornar `AgentResponse`) esta en `core/`.

```python
class TourismMultiAgent(MultiAgentOrchestrator):
    def __init__(
        self,
        openai_api_key=None,
        ner_service=None,          # NERServiceInterface (Phase 0)
        nlu_service=None,          # NLUServiceInterface (Phase 0)
        places_service=None,       # PlacesServiceInterface (Phase 1)
        directions_service=None,   # DirectionsServiceInterface (Phase 1)
        accessibility_service=None,# AccessibilityServiceInterface (Phase 1)
    ):
        llm = ChatOpenAI(model="gpt-4", temperature=0.3, max_tokens=2500)
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)
        # Foundation tools (always available)
        self.nlu = TourismNLUTool(nlu_service=nlu_service)
        self.location_ner = LocationNERTool(ner_service=ner_service)
        # Phase 1 domain tools (created when services injected)
        self._places_tool = PlacesSearchTool(places_service) if places_service else None
        self._directions_tool = DirectionsTool(directions_service) if directions_service else None
        self._accessibility_enrichment_tool = AccessibilityEnrichmentTool(accessibility_service) if accessibility_service else None
        # Legacy tools (fallback when no services injected)
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()

    async def _execute_pipeline_async(self, user_input, profile_context=None):
        # Step 1: NLU + NER in parallel (native async)
        nlu_raw, ner_raw = await asyncio.gather(
            self.nlu._arun(user_input), self.location_ner._arun(user_input)
        )
        # Step 1b: EntityResolver merges NLU + NER outputs
        nlu_result = self._parse_nlu_result(nlu_parsed)
        ner_locations, ner_top = self._parse_ner_locations(ner_parsed)
        resolved_entities = self.entity_resolver.resolve(nlu_result, ner_locations, ner_top)
        # Step 1c: Build typed pipeline context
        ctx = ToolPipelineContext(
            user_input=user_input, profile_context=profile_context,
            nlu_result=nlu_result, resolved_entities=resolved_entities, ...
        )
        # Step 2: Domain tools (Phase 1 if available, otherwise legacy)
        if self._places_tool:
            ctx = await self._places_tool.execute(ctx)
            ctx = await self._accessibility_enrichment_tool.execute(ctx)
            ctx = await self._directions_tool.execute(ctx)
        else:
            # Legacy sequential pipeline (TourismInfoTool, AccessibilityTool, RouteTool)
            ...
        return tool_results, metadata
```

### Tools especializados

#### Foundation Tools
| Tool | Clase | Input | Output |
|------|-------|-------|--------|
| NLU | `TourismNLUTool` | Texto del usuario | Intent, entities, accessibility type |
| Location NER | `LocationNERTool` | Texto del usuario (crudo) | `locations`, `top_location`, `provider`, `model`, `status` |

#### Phase 1 Domain Tools (API-First)
| Tool | Clase | Proveedor | Fallback | Output |
|------|-------|-----------|----------|--------|
| Places Search | `PlacesSearchTool` | Google Places API (New) v1 | `LocalPlacesService` | `PlaceCandidate`, `VenueDetail` |
| Directions | `DirectionsTool` | Google Routes v2 + OpenRouteService | `LocalDirectionsService` | `list[RouteOption]` |
| Accessibility | `AccessibilityEnrichmentTool` | Overpass/OSM | `LocalAccessibilityService` | `AccessibilityInfo` |

#### Legacy Tools (backward compat)
| Tool | Clase | Nota |
|------|-------|------|
| Accesibilidad | `AccessibilityAnalysisTool` | Usada solo si no se inyecta `accessibility_service` |
| Rutas | `RoutePlanningTool` | Usada solo si no se inyecta `directions_service` |
| Info turistica | `TourismInfoTool` | Usada solo si no se inyecta `places_service` |

Todas las Phase 1 tools operan sobre `ToolPipelineContext` (Pydantic) con firma `execute(ctx) -> ctx`. Las legacy tools extienden `langchain.tools.BaseTool`.

### Datos y servicios externos

#### Datos estáticos (fallback / local provider)

Los datos mock de Madrid están en `business/domains/tourism/data/` y son consumidos por los servicios locales:

| Módulo | Contenido | Consumido por |
|--------|-----------|---------------|
| `nlu_patterns.py` | Patrones de intent, destino, accesibilidad | `TourismNLUTool` (keyword fallback) |
| `accessibility_data.py` | `ACCESSIBILITY_DB` - scores, facilities | `LocalAccessibilityService` |
| `route_data.py` | `ROUTE_DB` - rutas metro/bus, costes | `LocalDirectionsService` |
| `venue_data.py` | `VENUE_DB` - horarios, precios, servicios | `LocalPlacesService` |

#### Servicios externos (Phase 1)

| Servicio | Proveedor | Interface ABC | Cliente |
|----------|-----------|---------------|---------|
| Búsqueda de lugares | Google Places API (New) v1 | `PlacesServiceInterface` | `GooglePlacesService` |
| Routing transit | Google Routes API v2 | `DirectionsServiceInterface` | `GoogleDirectionsService` |
| Routing wheelchair | OpenRouteService | `DirectionsServiceInterface` | `OpenRouteDirectionsService` |
| Accesibilidad | Overpass API (OSM) | `AccessibilityServiceInterface` | `OverpassAccessibilityService` |
| Geocoding | Nominatim (OSM) | `GeocodingServiceInterface` | `NominatimGeocodingService` + `CachedGeocodingService` |

Geocoding es un servicio compartido consumido por `DirectionsTool` y `AccessibilityEnrichmentTool` para resolver coordenadas desde nombres de lugar.

Selección via `.env`: `VOICEFLOW_PLACES_PROVIDER=local|google`, etc. Factories en `integration/external_apis/`.

## Decisiones arquitectonicas

### STT como servicio independiente (no como agente LangChain)

El STT es infraestructura, no logica de negocio:
- Menor latencia (sin overhead de LLM para audio)
- Control directo sobre el audio (formatos, sample rate, conversion)
- Fallback chain independiente (Azure -> Whisper -> simulacion)
- Testeable sin API keys de OpenAI

### Orquestacion híbrida (paralela + secuencial)

NLU y LocationNER se ejecutan en paralelo (async-native con `await asyncio.gather()`). Luego las Phase 1 domain tools se ejecutan en secuencia: PlacesSearch → AccessibilityEnrichment → Directions. El pipeline usa `ToolPipelineContext` (Pydantic) como acumulador tipado entre todas las tools. La orquestación sigue siendo fija (no selectiva por intent), lo cual permanece como deuda técnica para Fase 2.

### Modo simulacion en el adapter

`LocalBackendAdapter._simulate_ai_response()` contiene ~110 lineas de respuestas hardcodeadas que permiten desarrollar y demostrar el frontend sin consumir creditos de OpenAI. Este codigo deberia moverse a un mock service separado.

## Ejemplo de interaccion

**Input**: "Necesito una ruta accesible al Museo del Prado para silla de ruedas"

1. **NLU Tool** detecta:
   - Intent: `route_planning`
   - Destination: `Museo del Prado`
   - Accessibility: `wheelchair`

2. **LocationNER Tool** extrae:
       - Locations: `["Museo del Prado", "Madrid"]`
       - Top location: `Museo del Prado`

3. **Accessibility Tool** retorna:
   - Score: 9.2/10
   - Facilities: rampas, banos adaptados, audioguias, caminos tactiles
   - Certification: ONCE

4. **Route Tool** retorna:
   - Metro Linea 2 hasta Banco de Espana (25 min, accesible)
   - Bus 27 hasta Cibeles (35 min, piso bajo)

5. **Tourism Tool** retorna:
   - Horario: 10:00-20:00 (L-S), 10:00-19:00 (Dom)
   - Precio: 15 EUR (gratis para visitantes con discapacidad + acompanante)
   - Contacto accesibilidad: +34 91 330 2800

6. **GPT-4** combina todo en respuesta conversacional en espanol.

## Documentacion relacionada

- [03_business_layer_design.md](design/03_business_layer_design.md) - SDD detallado de business layer (actualizado post-Fase 2B)
- [04_application_layer_design.md](design/04_application_layer_design.md) - SDD del adapter y servicios
- [02_integration_layer_design.md](design/02_integration_layer_design.md) - SDD del pipeline STT
- [ROADMAP.md](ROADMAP.md) - Plan de evolucion del proyecto
- [PROPOSAL_FASE_2B.md](PROPOSAL_FASE_2B.md) - Propuesta y SDD de la descomposicion
