# Plan por Fases — Evolución de PlacesSearchTool a Producción

**Fecha:** 7 de Marzo de 2026  
**Ámbito:** `PlacesSearchTool` en pipeline turístico (`NLU + NER -> Places -> Accessibility -> Directions -> LLM`)  
**Objetivo global:** mejorar precisión, reducir consultas redundantes y maximizar valor/coste de Google Places API sin romper compatibilidad.

---

## 1) Contexto actual (baseline)

- `PlacesSearchTool` está activo en pipeline de Fase 1 y se ejecuta en secuencia tras NLU+NER.
- Hoy la búsqueda no usa políticas explícitas por intent (restaurant/museum/night_leisure/etc.).
- Se detectan queries duplicadas o poco informativas (p.ej. `"Almería Almería"`).
- Con provider `local` funciona como fallback seguro; con `google` depende de API key y disponibilidad.

---

## 2) Objetivos funcionales de la mejora

1. **Intent-aware search:** no tratar igual búsquedas de restaurante, museo, ocio nocturno, transporte, etc.
2. **Query hygiene:** evitar duplicaciones y construir consultas canónicas más precisas.
3. **Google API optimization:** aumentar relevancia top-1/top-3 minimizando latencia y coste.
4. **Rollout seguro:** feature flags, métricas y fallback automático a `local`.

---

## 3) Plan por fases

## Fase 0 — Hardening de baseline y observabilidad

### Objetivo
Establecer métricas y trazabilidad para comparar mejoras sin riesgo funcional.

### Alcance
- Añadir logging estructurado en `PlacesSearchTool`:
  - `intent`, `destination`, `query_original`, `query_final`, `provider`, `candidate_count`, `fallback_used`, `duration_ms`.
- Añadir métricas por intent:
  - latencia p50/p95, tasa de fallback, tasa de errores, candidates por consulta.
- Definir dataset de evaluación offline (consultas reales por categorías: restaurante/museo/ocio/ruta).

### Entregables
- Instrumentación y dashboard mínimo.
- Baseline de calidad (top-1/top-3) y coste estimado por consulta.

### Criterio de salida
- Baseline medido durante al menos 3-5 días o N consultas representativas.

---

## Fase 1 — Intent-aware policy (sin romper contrato)

### Objetivo
Introducir políticas de búsqueda diferenciadas por intent NLU.

### Alcance
- Crear `IntentSearchPolicy` (tabla intent -> estrategia):
  - `restaurant_search` -> tipos comida/restauración, sesgo por precio/valoración.
  - `museum_search` / `cultural_visit` -> tipos culturales/museos.
  - `night_leisure` -> tipos ocio nocturno.
  - `route_planning` -> priorizar POI/resolved destination sin ampliar ruido.
- Aplicar policy en `PlacesSearchTool` para construir mejor query y filtros.
- Mantener fallback a policy genérica si intent desconocido.

### Entregables
- Policy versionada (`v1`) + tests unitarios por intent.
- Comparativa online/offline vs baseline.

### Criterio de salida
- Mejora significativa de relevancia top-1/top-3 por intent (objetivo sugerido: +10% top-1 global).

---

## Fase 2 — Query Builder canónico (deduplicación y normalización)

### Objetivo
Eliminar consultas redundantes y mejorar calidad semántica de la query enviada.

### Alcance
- Implementar `QueryBuilder` con reglas:
  - deduplicación `query/location` cuando son equivalentes.
  - normalización de texto (trim, casing, acentos opcional, tokens repetidos).
  - priorización de `resolved_entities.destination` sobre texto libre.
  - fallback controlado a `user_input` solo si faltan señales estructuradas.
- Registrar en metadata interna:
  - `query_original`, `query_final`, `dedupe_applied`, `normalization_flags`.

### Entregables
- Módulo `query_builder` + tests (casos conflictivos reales).
- Reducción de queries con repetición de tokens.

### Criterio de salida
- 0 casos de duplicación obvia en corpus de validación.
- Reducción medible de consultas ambiguas/no accionables.

---

## Fase 3 — Optimización avanzada de Google Places API

### Objetivo
Aprovechar mejor la API para maximizar precisión con coste controlado.

### Alcance
- Estrategia multi-paso:
  1. **Search liviano** (field mask mínimo, max resultados acotado).
  2. **Rerank** por señales (intent-fit, rating, accesibilidad, cercanía, calidad de match).
  3. **Details selectivo** solo para top-N (evitar detalles masivos).
- Afinar `languageCode`, `maxResultCount`, filtros por categoría y sesgo geográfico.
- Integrar límites de resiliencia/presupuesto:
  - rate limiter, budget hourly, circuit breaker.

### Entregables
- Estrategia `search+rerank+details` activable por flag.
- Informe de coste/latencia antes y después.

### Criterio de salida
- Mantener latencia dentro de SLA (objetivo sugerido p95 no degradado >15%).
- Mejora neta de relevancia con coste estable o mejor.

---

## Fase 4 — Rollout controlado en producción

### Objetivo
Activar mejoras gradualmente minimizando riesgo.

### Alcance
- Feature flags recomendados:
  - `VOICEFLOW_PLACES_INTENT_POLICY_ENABLED`
  - `VOICEFLOW_PLACES_QUERY_BUILDER_V2_ENABLED`
  - `VOICEFLOW_PLACES_GOOGLE_OPTIMIZED_MODE`
- Despliegue progresivo:
  - 10% tráfico -> 50% -> 100%.
- Modo shadow opcional de comparación de calidad entre estrategia legacy y nueva.

### Entregables
- Playbook de rollback inmediato (volver a `local` o policy legacy).
- Checklist Go/No-Go de producto + SRE.

### Criterio de salida
- KPIs estables durante ventana de observación definida.
- Sin incremento relevante de errores/fallback inesperado.

---

## 4) Requisitos de activación en producción

- Variables mínimas:
  - `VOICEFLOW_USE_REAL_AGENTS=true`
  - `VOICEFLOW_PLACES_PROVIDER=google`
  - `GOOGLE_API_KEY=<valida>`
- Recomendado para fase avanzada:
  - timeouts y límites de resiliencia ajustados a SLA.
  - presupuesto por hora definido y monitorizado.

---

## 5) KPIs propuestos por fase

1. **Calidad**
   - Top-1 relevance por intent
   - Top-3 relevance por intent
2. **Operación**
   - Latencia p50/p95 de PlacesSearchTool
   - Error rate y fallback rate (`google -> local`)
3. **Coste**
   - Coste estimado por 1k consultas
   - Requests de details por consulta

---

## 6) Riesgos y mitigaciones

- **Riesgo:** sobre-filtrado por intent reduce recall.  
  **Mitigación:** fallback a policy genérica + A/B por intent.

- **Riesgo:** mayor coste por uso intensivo de details.  
  **Mitigación:** details solo top-N + budget guardrail.

- **Riesgo:** dependencia de API externa (quota/outage).  
  **Mitigación:** circuit breaker + fallback local + alertas.

---

## 7) Definición de éxito (DoD global)

- Intent-aware search operativo para intents principales.
- Eliminación de duplicaciones de query en producción.
- Mejora cuantificada de precisión con coste/latencia bajo control.
- Rollout completo con rollback probado y documentación actualizada.
