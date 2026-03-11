# Estado Actual del Sistema: Profile-Driven Tourism Recommendations

**Fecha:** 11 de Marzo de 2026
**Versión:** 2.1 (Post Fase 0 + Fase 1 + branch feature/real-tools-implementation)
**Objetivo:** Documentar claramente qué funciona y qué NO funciona en el sistema actual
**Última auditoría:** [AUDIT_2026_03_11.md](Reviews/AUDIT_2026_03_11.md)

---

## 📊 Resumen Ejecutivo

| Componente | Estado | Funcional? | Notas |
|-----------|--------|-----------|-------|
| **UI Selector de Perfiles** | ✅ Implementado | ✅ **SÍ** funciona | Usuario puede seleccionar profile_id desde UI |
| **Backend recibe Profile** | ✅ Implementado | ✅ **SÍ** funciona | `backend_adapter.py` recibe y resuelve profile_context |
| **ProfileService** | ✅ Implementado | ✅ **SÍ** funciona | Carga profiles.json correctamente |
| **Profile → Tools** | ⚠️ Parcial | ⚠️ **PARCIAL** | `ToolPipelineContext` transporta `profile_context`; `DirectionsTool` usa wheelchair needs |
| **Tools con datos reales** | ✅ API-First | ✅ **SÍ** funciona | Google Places, Google Routes, OpenRouteService, Overpass/OSM con fallback a mock |
| **Profile → Ranking** | ❌ NO implementado | ❌ **NO** funciona | No hay ranking real de venues |
| **Profile → LLM texto** | ⚠️ Parcial | ⚠️ **PARCIAL** | Solo afecta tono, no contenido estructurado |
| **NLU Tool** | ✅ Provider-based | ✅ **SÍ** funciona | OpenAI (`gpt-4o-mini`) con fallback keyword y trazabilidad en metadata |
| **JSON extraction** | ✅ Normalizada en adapter | ✅ **SÍ** funciona | Contrato estable en `metadata.tool_outputs` para NLU/NER |
| **Contratos tipados** | ✅ Implementado | ✅ **SÍ** funciona | `ToolPipelineContext` con 6 modelos Pydantic (Fase 0) |
| **Pipeline async-native** | ✅ Implementado | ✅ **SÍ** funciona | `await asyncio.gather()` directo, sin `asyncio.run()` anidado |
| **Resiliencia APIs** | ✅ Implementado | ✅ **SÍ** funciona | Circuit breaker + rate limiter + budget tracker |
| **EntityResolver** | ✅ Implementado | ✅ **SÍ** funciona | Merge NLU + NER outputs con política explícita |
| **Geocoding** | ✅ Implementado | ✅ **SÍ** funciona | Nominatim + cache + fallback local (usado por Directions + Accessibility) |

---

## 1. Infraestructura de Perfiles: ✅ FUNCIONANDO

### ¿Qué SÍ funciona?

#### 1.1 Flujo UI → Backend
```
┌─────────────────────────────────────────────────────────────┐
│ UI (templates/index.html)                                   │
│ - Selector de perfiles: night_leisure, cultural, etc.      │
│ - Envía: {"active_profile_id": "night_leisure"}            │
└────────────────────┬────────────────────────────────────────┘
                     │ POST /api/v1/chat/message
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (backend_adapter.py)                      │
│ - Recibe user_preferences                                   │
│ - Llama ProfileService.resolve_profile()                    │
│ - Construye profile_context con:                            │
│   * prompt_directives                                       │
│   * ranking_bias (NO USADO actualmente)                     │
└────────────────────┬────────────────────────────────────────┘
                     │ profile_context
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Business Layer (agent.py)                                   │
│ - Recibe profile_context                                    │
│ - Lo usa en _build_response_prompt() → SOLO TEXTO          │
│ - LLM lee prompt con directives del perfil                  │
└─────────────────────────────────────────────────────────────┘
```

**✅ Verificado:**
- [ProfileService](../application/services/profile_service.py) carga profiles.json correctamente
- [backend_adapter.py#L185-L195](../application/orchestration/backend_adapter.py) construye profile_context
- [agent.py](../business/domains/tourism/agent.py) recibe profile_context como parámetro
- Logs muestran: `profile_resolved: true`, `active_profile_id: "night_leisure"`

---

## 2. Tools (Herramientas): ✅ Foundation + Domain tools operativas

### Estado real de tools en Marzo 2026 (Post Fase 0 + Fase 1)

#### 2.1 Foundation Tools (Producción)

| Tool | Estado | Proveedor |
|------|--------|-----------|
| **NLU Tool** | ✅ Robusto | OpenAI (`gpt-4o-mini`) + keyword fallback + shadow mode |
| **LocationNER** | ✅ Robusto | spaCy `es_core_news_md` con contrato estable |

#### 2.2 Domain Tools — Fase 1 (Nuevas, API-First)

| Tool | Proveedor | Fallback | Interface ABC |
|------|-----------|----------|---------------|
| **PlacesSearchTool** | Google Places API (New) v1 | `LocalPlacesService` (VENUE_DB) | `PlacesServiceInterface` |
| **DirectionsTool** | Google Routes v2 + OpenRouteService | `LocalDirectionsService` (ROUTE_DB) | `DirectionsServiceInterface` |
| **AccessibilityEnrichmentTool** | Overpass/OSM | `LocalAccessibilityService` (ACCESSIBILITY_DB) | `AccessibilityServiceInterface` |

#### 2.2b Supporting Services (Fase 1)

| Service | Proveedor | Fallback | Interface ABC |
|---------|-----------|----------|---------------|
| **Geocoding** | Nominatim (OSM) | `LocalGeocodingService` | `GeocodingServiceInterface` |
| **CachedGeocoding** | Cache wrapper (TTL 1h) | Delegated provider | `GeocodingServiceInterface` |

Geocoding es consumido por `DirectionsTool` y `AccessibilityEnrichmentTool` para resolver coordenadas.

Selección de proveedor via `.env`: `VOICEFLOW_PLACES_PROVIDER=local|google`, etc.
**Nota:** El default de todos los providers es `local` (datos mock). Para APIs reales, configurar explícitamente en `.env`.

#### 2.3 Domain Tools — Legacy (Backward compat)

| Tool | Estado | Nota |
|------|--------|------|
| **AccessibilityAnalysisTool** | ⚠️ Legacy | Se usa solo si no se inyecta `accessibility_service` |
| **RoutePlanningTool** | ⚠️ Legacy | Se usa solo si no se inyecta `directions_service` |
| **TourismInfoTool** | ⚠️ Legacy | Se usa solo si no se inyecta `places_service` |

#### 2.4 Pipeline tipado (Fase 0)

Todas las tools operan sobre `ToolPipelineContext` — un acumulador Pydantic que fluye por el pipeline:

```python
class ToolPipelineContext(BaseModel):
    user_input: str
    language: str = "es"
    profile_context: Optional[dict] = None
    nlu_result: Optional[NLUResult] = None
    resolved_entities: Optional[ResolvedEntities] = None
    place: Optional[PlaceCandidate] = None       # includes GeocodedLocation fields
    accessibility: Optional[AccessibilityInfo] = None
    routes: list[RouteOption] = []
    venue_detail: Optional[VenueDetail] = None
    raw_tool_results: dict[str, str] = {}
    errors: list[ToolError] = []

# Additional models (Fase 0+1):
# - GeocodedLocation: latitude, longitude, formatted_address, confidence, source
# - ToolError: source, message (partial errors without breaking pipeline)
```

#### 2.5 Ejemplo: Query sobre Granada (con APIs reales configuradas)

```bash
# Query: "Recomiéndame la Alhambra en Granada"
# Con VOICEFLOW_PLACES_PROVIDER=google y Google API key configurada:

# NLU Tool: intent=venue_search, destination=Alhambra
# LocationNER: extracts "Alhambra", "Granada"
# PlacesSearchTool: Google Places busca "Alhambra Granada" → place_id, coords, rating, wheelchair fields
# AccessibilityEnrichmentTool: Overpass OSM wheelchair tags near coords
# DirectionsTool: Google Routes/ORS calcula rutas reales

# Resultado: Tools APORTAN datos reales + tourism_data poblado
```

```bash
# Con VOICEFLOW_PLACES_PROVIDER=local (default, sin API keys):

# PlacesSearchTool: fallback a LocalPlacesService → busca en VENUE_DB
# Comportamiento idéntico al anterior (mock data)
# El LLM sigue usando su conocimiento pre-entrenado como fallback
```

**Conclusión:**
- ✅ Con API keys configuradas: datos estructurados reales de cualquier ciudad
- ✅ Sin API keys (default): fallback automático a mock data, sin errores
- ✅ `LocationNER` aporta señal estructurada consumible en pipeline
- ✅ Pipeline tipado (`ToolPipelineContext`) garantiza contratos entre tools

### Estado específico de NLU/NER (Commit NLU-5)

- `NLU` y `LocationNER` se ejecutan en paralelo y luego se continúa con tools de dominio.
- Input de `LocationNER` en modo real: **texto crudo del usuario/transcripción** (`user_input`), no `nlu_raw`.
- Output de NER/NLU expuesto en API:
    - `entities.location_ner`
    - `metadata.tool_outputs.location_ner`
    - `metadata.tool_outputs.nlu`
    - `metadata.tool_results_parsed.nlu` (trazabilidad interna)
    - `metadata.tool_results_parsed.locationner` (trazabilidad interna)
- Este estado permite validación end-to-end de NLU/NER aun cuando otras tools sigan en modo stub.

### EntityResolver (Post NLU-3)

`EntityResolver` (`business/domains/tourism/entity_resolver.py`) combina los outputs de NLU y NER:
- NLU aporta: `intent`, `entities.destination`, `entities.accessibility`
- NER aporta: `locations[]`, `top_location`
- El resolver aplica política de merge explícita para producir `ResolvedEntities`
- Resultado usado por `PlacesSearchTool` para construir búsquedas

---

## 3. Profile Context: ⚠️ PARCIAL — afecta texto + wheelchair routing, no ranking

### ¿Qué funciona ahora?

#### 3.1 Profile transportado en pipeline tipado

```python
# En agent.py — pipeline async
ctx = ToolPipelineContext(
    user_input=user_input,
    profile_context=profile_context,  # ← AHORA transportado
    ...
)
ctx = await self._places_tool.execute(ctx)        # puede leer ctx.profile_context
ctx = await self._accessibility_enrichment_tool.execute(ctx)
ctx = await self._directions_tool.execute(ctx)     # usa wheelchair needs del perfil
```

**Mejoras respecto a v1.2:**
- `ToolPipelineContext` transporta `profile_context` a todas las tools
- `DirectionsTool` detecta `wheelchair` en `profile_context.accessibility_needs` y solicita routing wheelchair
- Los demás tools aún no filtran por perfil

### ¿Qué NO funciona?

#### 3.2 Profile SÍ afecta el prompt (texto)

```python
# En response_prompt.py (línea ~33)
def build_response_prompt(..., profile_context):
    profile_section = f"""
PERFIL ACTIVO: {profile_context.get("label")}
Directivas del perfil:
{chr(10).join(f"- {d}" for d in directives)}
"""
```

**Resultado:**
- El LLM lee las directivas del perfil
- Ajusta el **tono** de la respuesta (más enfocado en ocio nocturno si profile=night_leisure)
- PERO: No afecta qué venues se seleccionan (porque tools son stubs)

#### 3.3 Ejemplo: Mismo Query, Diferentes Perfiles

```bash
# Query: "Recomiéndame actividades en Madrid esta noche"

# Con profile="night_leisure":
# → LLM menciona bares, discotecas (TONO ajustado)
# → Pero tools devolvieron "Museo del Prado" (DATOS no ajustados)
# → Contradicción entre texto y datos estructurados

# Con profile="cultural":
# → LLM menciona museos, exposiciones (TONO ajustado)
# → Pero tools devolvieron "Museo del Prado" (MISMOS DATOS)
# → NO hay sesgo real en los datos
```

---

## 4. Contrato estructurado de salida: ✅ Estable en adapter

### Estado actual

```python
# application/orchestration/backend_adapter.py
# contrato estable para consumidores
metadata.tool_outputs = {
    "nlu": {...payload normalizado...},
    "location_ner": {...payload normalizado...}
}
```

**Resultado actual:**
- NLU/NER quedan siempre normalizados para consumo API/UI en `metadata.tool_outputs`.
- Se mantiene `metadata.tool_results_parsed` para diagnóstico interno sin romper contrato público.
- `tourism_data` continúa condicionado por tools de dominio stub (gap de datos, no de extracción NLU/NER).

---

## 5. ¿Qué FUNCIONA en la práctica?

### ✅ Lo que SÍ funciona

1. **Conversación básica**: El LLM responde coherentemente
2. **Infraestructura técnica**: FastAPI, Docker, STT, todo funcional
3. **Flujo de datos**: UI → Backend → Agent → LLM → Response funciona
4. **Profiles (estructural)**: Infraestructura lista, `profile_context` transportado en pipeline
5. **Tools con datos reales**: Google Places, Google Routes, OpenRouteService, Overpass/OSM (con API keys)
6. **Fallback automático**: Sin API keys → datos mock, sin errores
7. **Pipeline async-native**: Sin `asyncio.run()` anidado, compatible con streaming/WebSockets
8. **Contratos tipados**: `ToolPipelineContext` con Pydantic models entre todas las tools
9. **Resiliencia**: Circuit breaker + rate limiter + budget tracker para APIs externas
10. **156 test functions** en 29 archivos incluyendo tests para Fase 0 + Fase 1

### ❌ Lo que NO funciona

1. **Profile-driven ranking**: El perfil NO afecta qué venues se seleccionan/priorizan
2. **Routing por intent**: Todas las tools se ejecutan siempre
3. **Seguridad**: Sin autenticación, sin rate limiting público, sin HTTPS
4. **Escalabilidad real**: Con `local` provider, sigue limitado a mock data de Madrid

---

## 6. Roadmap: ¿Qué hace falta?

> **Fuente de verdad para roadmap completo:** [ROADMAP.md](ROADMAP.md)

### Resumen de próximos pasos

| Prioridad | Fase | Estado |
|-----------|------|--------|
| ~~1~~ | ~~Fase 0: Contratos~~ | ✅ COMPLETADA |
| ~~1b~~ | ~~Fase 1: Tools reales API-First~~ | ✅ COMPLETADA |
| 2 | Fase 2: Seguridad + Routing por Intent | PENDING |
| 3 | Profile → Ranking | PENDING |
| 4 | Consolidar payloads dominio | PARTIAL |

---

## 7. Decisiones Pendientes

### ~~Decisión 1: ¿Qué estrategia para tools?~~ ✅ RESUELTA
**Elegida: Opción A (APIs Externas)** — implementado en Fase 1 con Google Places, Google Routes, OpenRouteService, Overpass/OSM. Fallback automático a datos mock (local) cuando no hay API keys.

### ~~Decisión 2: ¿Cuándo implementar Fase 0?~~ ✅ RESUELTA
**Elegida: Opción A (Ahora)** — Fases 0 y 1 completadas.

### Decisión 3: ¿Estrategia de seguridad?

| Opción | Pros | Contras |
|--------|------|---------|
| **A: JWT tokens** | Estándar, stateless | Más complejo de implementar |
| **B: API keys** | Simple, rápido | Menos granular |

**Recomendación:** **B (API keys)** para PoC, migrar a **A (JWT)** si se necesita multi-tenant.

### Decisión 4: ¿Routing por intent o fan-out?

| Opción | Pros | Contras |
|--------|------|---------|
| **A: Routing selectivo** | Menor latencia, menos coste API | Requiere mapeo intent→tools |
| **B: Fan-out completo** | Más datos disponibles para LLM | Mayor latencia y coste |

**Recomendación:** **A (Routing selectivo)** — mapear intents de NLU a subconjuntos de tools.

---

## 8. Conclusiones

### Estado del Sistema: "PoC Funcional con Stack API-First"

El sistema ha evolucionado de prototipo arquitectónico a **PoC funcional**:
- ✅ Arquitectura en 4 capas sólida y bien separada
- ✅ Integración LangChain + OpenAI funciona
- ✅ Flujo de perfiles implementado (infraestructura + wheelchair routing)
- ✅ Tools con datos reales: Google Places, Google Routes, OpenRouteService, Overpass/OSM
- ✅ Fallback automático a datos mock sin errores
- ✅ Pipeline async-native con contratos tipados (Pydantic)
- ✅ Capa de resiliencia: circuit breaker + rate limiter + budget tracker
- ✅ 128 tests pasan

**Pendiente:**
- ⚠️ El perfil NO afecta ranking/filtrado de venues (solo tono + wheelchair routing)
- ⚠️ Orquestación secuencial fija (sin routing por intent)
- ❌ Sin autenticación ni rate limiting público (B4)

### Siguiente Paso Crítico

**Fase 2: Seguridad + Routing por Intent**

La base técnica está lista. El siguiente salto debe centrarse en seguridad (B4) y routing inteligente por intent para reducir latencia y coste.

---

**Autor:** GitHub Copilot (GPT-5.3-Codex) + Claude Opus 4.6
**Última actualización:** 11 Mar 2026 (auditoría documental)
