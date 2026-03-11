# Auditoría Técnica Actualizada -- VoiceFlow Tourism Multi-Agent System

**Fecha de generación:** 05 March 2026

------------------------------------------------------------------------

## 1. Resumen Ejecutivo

El sistema ha evolucionado significativamente. Con la implementación de
Fase 0 (Contratos y Plumbing) y Fase 1 (Tools Reales — Stack API-First),
se han resuelto los bloqueadores críticos B1-B3 de la auditoría arquitectónica.

### Fortalezas actuales

-   Arquitectura en 4 capas sólida y bien separada.
-   NLU provider-based (OpenAI + fallback) con shadow mode.
-   LocationNER real con spaCy.
-   Pipeline async-native con `await asyncio.gather()` directo (B2 resuelto).
-   Contratos tipados inter-tool vía `ToolPipelineContext` (Pydantic) (B3 resuelto).
-   Contrato estructurado estable en `metadata.tool_outputs`.
-   Stack API-First con 4 proveedores reales: Google Places (New), Google Routes, OpenRouteService, Overpass/OSM.
-   Abstracciones SOLID — 3 ABCs + factories con fallback automático a datos mock (B1 resuelto).
-   Capa de resiliencia: circuit breaker, rate limiter, budget tracker.
-   128 tests pasan (42 nuevos de Fase 0 + 1).

### Bloqueadores resueltos

| ID | Descripción | Resolución |
|----|-------------|------------|
| B1 | Tools de dominio son stubs | PlacesSearchTool, DirectionsTool, AccessibilityEnrichmentTool con proveedores reales |
| B2 | `asyncio.run()` anidado | Pipeline async-native con `await` directo |
| B3 | Sin contratos tipados inter-tool | `ToolPipelineContext` con 6 modelos Pydantic |

### Bloqueadores pendientes

-   B4: Zero security (sin auth, sin HTTPS, sin rate limiting público).
-   `profile_context` no afecta realmente a las tools (pendiente: ranking).
-   Orquestación secuencial fija (no hay routing por intent).
-   No hay ranking real ni filtrado por perfil.

------------------------------------------------------------------------

## 2. Estado Arquitectónico

### Arquitectura

-   4 capas bien definidas: presentation, application, business, integration.
-   Interfaces y DI correctamente implementados (6 ABCs: NLU, NER, Places, Directions, Accessibility, Backend).
-   BackendAdapter bien posicionado como capa de coordinación — ahora crea servicios via factories.
-   Patrón Factory + Registry para todos los proveedores externos.

Evaluación: **9.0 / 10** (antes: 8.5)

------------------------------------------------------------------------

## 3. Estado de Tools

### 3.1 Foundation Tools (Sólidas)

  Tool          Estado       Comentario
  ------------- ------------ -------------------------------
  TourismNLU    ✅ Robusto   Provider-based + shadow mode
  LocationNER   ✅ Robusto   spaCy real + contrato estable

### 3.2 Domain Tools — Phase 1 (Nuevas)

  Tool                      Estado         Proveedor                    Fallback
  ------------------------- -------------- ---------------------------- --------
  PlacesSearchTool          ✅ Implementado Google Places API (New) v1   LocalPlacesService (VENUE_DB)
  DirectionsTool            ✅ Implementado Google Routes + OpenRouteService  LocalDirectionsService (ROUTE_DB)
  AccessibilityEnrichment   ✅ Implementado Overpass/OSM                 LocalAccessibilityService (ACCESSIBILITY_DB)

### 3.3 Domain Tools — Legacy (Backward compat)

  Tool            Estado       Nota
  --------------- ------------ ----------------------------------------
  Accessibility   ⚠️ Legacy    Se usa solo si no hay servicio inyectado
  RoutePlanning   ⚠️ Legacy    Se usa solo si no hay servicio inyectado
  TourismInfo     ⚠️ Legacy    Se usa solo si no hay servicio inyectado

Las tools legacy se mantienen para backward compatibility. Cuando se inyectan
servicios Phase 1 (por defecto desde `backend_adapter.py`), las nuevas tools
toman precedencia automáticamente.

------------------------------------------------------------------------

## 4. Profile System

### Lo que funciona

-   UI envía `active_profile_id`.
-   Backend construye `profile_context`.
-   El prompt final lo utiliza para tono.
-   `ToolPipelineContext` transporta `profile_context` a todas las tools.
-   `DirectionsTool` ya consume `profile_context.accessibility_needs` para wheelchair routing.

### Lo que NO funciona

-   No existe ranking real por perfil.
-   No hay filtrado de venues por preferencias del perfil.

Conclusión: El perfil es parcialmente funcional — afecta routing wheelchair pero no ranking.

------------------------------------------------------------------------

## 5. Orquestación Actual

### Estado actual

-   NLU + NER en paralelo (async-native).
-   Pipeline tipado: `ToolPipelineContext` fluye entre tools.
-   Resto del pipeline secuencial: Places → Accessibility → Directions.
-   No hay routing por intent.

### Mejoras respecto a versión anterior

-   Eliminado `asyncio.run()` anidado — ahora `await` directo.
-   Cada tool recibe y devuelve `ToolPipelineContext` tipado.
-   Errores parciales se registran en `ctx.errors` sin romper el pipeline.

### Limitaciones pendientes

-   Se ejecutan todas las tools siempre (sin routing por intent).
-   No hay fan-out / fan-in real.

------------------------------------------------------------------------

## 6. Capa de Resiliencia (Nueva)

-   **CircuitBreaker**: CLOSED/OPEN/HALF_OPEN por servicio, threshold configurable.
-   **TokenBucketRateLimiter**: async-safe, configurable RPS.
-   **BudgetTracker**: ventana horaria con coste estimado por operación.
-   **ResilienceManager**: fachada unificada vía `pre_request(service, operation)`.

Todas las llamadas a APIs externas pasan por la capa de resiliencia.

------------------------------------------------------------------------

## 7. Stack de Proveedores (Fase 1)

| Servicio | Proveedor | Coste | Interface |
|----------|-----------|-------|-----------|
| Búsqueda de lugares | Google Places API (New) v1 | Free tier (10K/mes) | `PlacesServiceInterface` |
| Routing transit | Google Routes API v2 | Free tier | `DirectionsServiceInterface` |
| Routing wheelchair | OpenRouteService | Gratuito | `DirectionsServiceInterface` |
| Accesibilidad | Overpass API (OSM) | Público, sin key | `AccessibilityServiceInterface` |
| Fallback | VENUE_DB, ROUTE_DB, ACCESSIBILITY_DB | $0 | Mismas interfaces |

Selección de proveedor via `.env`: `VOICEFLOW_PLACES_PROVIDER=local|google`, etc.

------------------------------------------------------------------------

## 8. Recomendaciones Estratégicas

### ~~Fase 0 -- Contratos y Plumbing~~ ✅ COMPLETADA

-   ToolPipelineContext + 6 modelos Pydantic.
-   Pipeline async-native.
-   LLM settings en Settings.
-   12 tests.

### ~~Fase 1 -- Tools reales (API-First)~~ ✅ COMPLETADA

-   4 clientes API + 3 fallbacks locales + 3 factories.
-   3 nuevas domain tools con DI.
-   Capa de resiliencia.
-   Wiring en agent.py + backend_adapter.py.
-   42 tests.

### Fase 2 -- Seguridad + Routing por Intent (Siguiente)

-   Implementar autenticación (JWT o API keys).
-   Routing por intent (ejecutar solo tools relevantes).
-   ProfileRankingTool para filtrado por perfil.
-   Rate limiting público.

### Fase 3 -- Migración a LangGraph

-   Modelar estado explícito del pipeline.
-   Nodes: nlu → ner → candidates → ranking → details → route → response.

------------------------------------------------------------------------

## 9. Riesgos Actuales

1.  Profile seguirá siendo parcial sin ranking real.
2.  ~~Al integrar APIs reales, latencia y coste sin control.~~ → Mitigado: ResilienceManager con budget tracker.
3.  Pipeline secuencial limita escalabilidad futura.
4.  **B4 (Seguridad)**: Sin auth ni rate limiting público — prioridad alta.

------------------------------------------------------------------------

## 10. Evaluación Final

  Área                    Antes    Ahora    Delta
  ----------------------- -------- -------- -------
  Arquitectura            8.5/10   9.0/10   +0.5
  Foundation Tools        8/10     8/10     =
  Dominio real            3/10     7/10     +4.0
  Orquestación avanzada   4/10     6/10     +2.0
  Resiliencia             0/10     7/10     +7.0
  Testing                 6/10     8/10     +2.0

El sistema ha dado un salto cualitativo significativo con las fases 0 y 1.

------------------------------------------------------------------------

**Conclusión:**\
Los bloqueadores críticos B1-B3 están resueltos. El stack API-First con
abstracciones SOLID permite cambiar de proveedor sin tocar lógica de negocio.
El siguiente salto debe centrarse en seguridad (B4), routing por intent
y ranking por perfil.
