# High Level Tools Contract Spec (SPEC_FILE)

**Fecha**: 2 de Marzo de 2026  
**Estado**: Activo (iteración conservadora)
**Precedencia**: Complementa `documentation/API_REFERENCE.md` para la feature HighLevelToolsSDD.

---

## 1. Objetivo

Definir el contrato técnico mínimo para implementar capacidades de turismo real sin acoplar la capa Business a proveedores concretos.

## 2. Reglas de compatibilidad

- No se rompe el contrato existente de `POST /api/v1/chat/message`.
- Cualquier payload nuevo debe ser opcional.
- Fuente estable para consumidores: `metadata.tool_outputs`.

## 3. Contrato de salida adicional

### 3.1 `metadata.tool_outputs.high_level_tools` (opcional)

```json
{
  "status": "active|fallback|disabled|error",
  "provider": "mock_tourism_data_provider",
  "profile_id": "tourism",
  "profile_label": "Turismo",
  "accessibility_match": {
    "score": 0.0,
    "matched_requirements": [],
    "missing_requirements": [],
    "requirements_source": "profile_context|query_inferred|unknown",
    "notes": "string|null"
  },
  "degradation": {
    "enabled": false,
    "reason": null
  }
}
```

### 3.2 Restricciones

- `status` debe ser uno de `active|fallback|disabled|error`.
- `accessibility_match.score` en rango `[0, 1]`.
- Si no hay `profile_context`, usar `requirements_source="unknown"`.

## 4. Contrato de proveedor abstracto

Interfaz requerida: `TourismDataProviderInterface`.

Métodos mínimos:
- `is_service_available() -> bool`
- `get_service_info() -> dict`
- `get_accessibility_insights(destination, accessibility_need, profile_context, language) -> dict`
- `plan_routes(origin_text, destination, accessibility_need, profile_context, language) -> dict`
- `get_tourism_info(destination, query_text, profile_context, language) -> dict`

## 5. Ambigüedades explícitas (TODO)

- TODO: `profile_context` actual no define requisitos explícitos de accesibilidad (`wheelchair`, `visual`, etc.).
- TODO: cuando exista contrato explícito de requisitos por perfil, reemplazar inferencia desde query.
- TODO: definir proveedor externo real (Google/OSM/etc.) en fase posterior.
