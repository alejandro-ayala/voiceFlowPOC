# Plan por fases: Accesibilidad Google Places + Overpass (comparativa real)

**Fecha:** 2026-03-07  
**Estado:** Propuesta inicial para implementación incremental  
**Objetivo:** Integrar señal de accesibilidad de Google Places en el flujo de `PlacesSearchTool`, mantener `AccessibilityEnrichmentTool` con Overpass como segunda fuente, y habilitar una comparativa real basada en datos completos de API.

---

## 1) Contexto y decisión técnica

### Decisión base
1. **No duplicar llamadas innecesarias a Google Places** en `AccessibilityEnrichmentTool`.
2. **Aprovechar los datos de accesibilidad de Google Places ya obtenibles** desde la fase de búsqueda/detalle de `PlacesSearchTool`.
3. **Mantener Overpass en `AccessibilityEnrichmentTool`** para:
   - complementar cobertura,
   - contrastar consistencia de datos,
   - decidir más adelante si se puede degradar o eliminar la segunda fuente.

### Requisito imprescindible de esta propuesta
`AccessibilityEnrichmentTool` (Overpass) **debe exponer el payload completo de respuesta de Overpass** para análisis comparativo real, incluso si eso va en:
- logs estructurados, y/o
- campo de depuración no fuertemente tipado (por ejemplo en `raw_tool_results` / `metadata`).

> Este punto es obligatorio para la fase de comparación. No se limita a mapear solo los campos que coinciden con Google.

---

## 2) Principios de implementación

- **Sin ruptura de contrato funcional** actual de `tourism_data.accessibility`.
- **Observabilidad primero**: trazabilidad explícita por fuente (`google_places`, `overpass_osm`, `local_db`).
- **Comparación reproducible**: conservar evidencia completa para auditoría técnica.
- **Incremental y reversible**: activar por flags/configuración para controlar latencia/coste.

---

## 3) Fases propuestas

## Fase 0 — Observabilidad y contratos de depuración (base)

### Objetivo
Preparar el pipeline para comparar fuentes sin cambiar todavía la lógica de decisión final.

### Entregables
1. Definir estructura de depuración no tipada para accesibilidad (ejemplo):
   - `metadata.tool_results_debug.accessibility.google_raw`
   - `metadata.tool_results_debug.accessibility.overpass_raw`
   - `metadata.tool_results_debug.accessibility.comparison`
2. Añadir logging estructurado para:
   - payload bruto de Overpass (con redacción de datos sensibles si aplica),
   - tamaño de payload,
   - tiempo por fuente,
   - resultado de normalización.
3. Documentar en `API_REFERENCE` que existen campos de depuración no estables para análisis.

### Criterio de aceptación
- Se puede inspeccionar una respuesta y ver claramente el raw completo de Overpass en metadata/debug/log.

---

## Fase 1 — Exponer accesibilidad Google desde PlacesSearchTool

### Objetivo
Hacer que `PlacesSearchTool` entregue también señal de accesibilidad Google sin llamada adicional redundante.

### Entregables
1. Incluir en salida de Places los campos de `accessibilityOptions` cuando estén disponibles:
   - `wheelchairAccessibleEntrance`
   - `wheelchairAccessibleParking`
   - `wheelchairAccessibleRestroom`
   - `wheelchairAccessibleSeating`
2. Persistir esta señal en contexto compartido para uso posterior de enriquecimiento/comparación.
3. Añadir `source` y `confidence_hint` por campo (cuando aplique) para trazabilidad.

### Criterio de aceptación
- Tras `PlacesSearchTool`, el contexto ya contiene accesibilidad Google usable por pasos posteriores.

---

## Fase 2 — Comparativa Google vs Overpass en AccessibilityEnrichmentTool

### Objetivo
Mantener Overpass como enriquecimiento y crear una comparativa objetiva entre ambas fuentes.

### Entregables
1. `AccessibilityEnrichmentTool` consume:
   - señal previa de Google (si existe),
   - respuesta Overpass.
2. Guardar **raw completo de Overpass** (obligatorio) en debug/log.
3. Generar bloque de comparación no tipado, por ejemplo:
   - `field_by_field`: coincide / difiere / no disponible,
   - `coverage`: qué fuente aporta más campos,
   - `conflicts`: lista de contradicciones,
   - `notes`: observaciones de calidad de datos.
4. Estrategia de merge inicial (simple y explícita):
   - Google como baseline comercial estructurado,
   - Overpass agrega granularidad (ramp, kerb, incline, tactile_paving, etc.).

### Criterio de aceptación
- Por cada consulta, existe evidencia completa para comparar Google vs Overpass con detalle.

---

## Fase 3 — Métricas y decisión de dependencia de Overpass

### Objetivo
Tomar decisión informada sobre mantener, degradar o desactivar Overpass en producción.

### Entregables
1. Métricas mínimas:
   - % consultas con datos útiles de Google,
   - % consultas con valor incremental real de Overpass,
   - % conflictos Google/Overpass,
   - impacto de latencia por activar Overpass.
2. Umbrales de decisión (ejemplo):
   - si Overpass aporta valor incremental en < X% y añade > Y ms medianos, pasar a modo opcional.
3. Feature flag para modo de operación:
   - `compare` (Google + Overpass),
   - `google_only`,
   - `overpass_only` (diagnóstico),
   - `local_fallback`.

### Criterio de aceptación
- Existe recomendación objetiva basada en datos reales, no percepción.

---

## Fase 4 — Hardening y documentación final

### Objetivo
Consolidar la solución elegida y dejar contrato/documentación alineados.

### Entregables
1. Actualización de documentación técnica:
   - arquitectura,
   - API reference,
   - guía operativa.
2. Tests:
   - unit (normalización + comparación),
   - integración (Google/Overpass mocks),
   - smoke e2e.
3. Política de logging y retención para payloads debug.

### Criterio de aceptación
- Pipeline estable, medible y documentado; sin ambigüedad entre diseño y comportamiento real.

---

## 4) Cambios de código esperados (alto nivel)

1. **`PlacesSearchTool`**
   - incluir accesibilidad Google en resultados estructurados.
2. **`AccessibilityEnrichmentTool`**
   - ejecutar enriquecimiento Overpass,
   - almacenar raw completo de Overpass en debug/log,
   - producir comparativa Google vs Overpass.
3. **Modelado y metadata**
   - mantener `AccessibilityInfo` tipado para salida funcional,
   - usar contenedor no tipado para debug/comparison detallada.
4. **Configuración**
   - flags para activar/desactivar comparativa y nivel de detalle en logs.

---

## 5) Riesgos y mitigaciones

1. **Latencia adicional por Overpass**
   - Mitigar con timeout corto + fallback + ejecución controlada por flag.
2. **Payloads grandes en logs/debug**
   - Mitigar con límites de tamaño, truncado seguro y redacción.
3. **Contradicciones entre fuentes**
   - Mitigar con política de prioridad explícita y campo `conflicts` visible.
4. **Desalineación documentación/código**
   - Mitigar con actualización documental en cada fase de entrega.

---

## 6) Resultado esperado

Al final de estas fases, el sistema podrá:
- usar accesibilidad de Google de forma eficiente,
- conservar Overpass como enriquecimiento y mecanismo de validación,
- demostrar con evidencia completa (incluyendo raw Overpass) si Overpass aporta valor suficiente o si puede desactivarse en producción.