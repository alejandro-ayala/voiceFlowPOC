# Plan de ejecución — Tool NLU INTENT+SLOTS (5 commits)

**Fecha**: 23 de Febrero de 2026  
**Rama**: `feature/real-ner-tool-implementation`  
**Objetivo**: Implementar una NLU robusta (intención + entidades/slots de negocio) configurable por entorno e idioma, desacoplada del proveedor concreto y alineada con el pipeline actual `NLU -> LocationNER -> Accessibility -> Routes -> Venue Info`.

---

## 1) Alcance y principios de implementación

### Requisitos obligatorios

- [ ] Mejorar NLU actual basada en regex/keywords para reducir dependencias de datos hardcodeados de Madrid.
- [ ] Mantener compatibilidad con el contrato actual de API (`intent`, `entities`, `pipeline_steps`) documentado en `documentation/API_REFERENCE.md`.
- [ ] Configuración por entorno para idioma/proveedor/modelos de NLU sin cambios de código cliente.
- [ ] Desacoplar Business/Application de la implementación NLU concreta (patrón interface + factory, igual que NER).
- [ ] Garantizar degradación graceful y observabilidad de la etapa NLU.

### Restricciones de arquitectura

- Capa `Business` **no** debe depender de librerías específicas del proveedor NLU.
- Capa `Shared` define contratos NLU; `Integration` implementa proveedores.
- Capa `Application` solo hace wiring por DI/factory.
- Mantener trazabilidad en `metadata.tool_results_parsed` y, de forma estable para consumidores, en `metadata.tool_outputs.nlu`.

### No-objetivos (esta iteración)

- No sustituir en esta fase todas las tools stub por APIs externas reales.
- No migrar todo el pipeline a function-calling estructurado en el mismo bloque de trabajo.
- No fusionar NLU y NER en una sola tool durante esta entrega (ver análisis en sección 2.4).

---

## 2) Definición funcional de la NLU Tool

### 2.1 Objetivo claro de la tool

Resolver, para cada mensaje del usuario:
1) **Intent** principal (p.ej. `route_planning`, `event_search`, `restaurant_search`, `accommodation_search`, `general_query`).
2) **Slots/entidades de negocio** consumibles por el resto del pipeline (destino normalizado, requisito de accesibilidad, horizonte temporal, preferencias de transporte, presupuesto, etc.).
3) **Señal de confianza** y alternativas para fallback controlado.

### 2.2 Inputs

- `text: str` (texto crudo de usuario o transcripción STT)
- `language: Optional[str]` (default desde settings)
- `profile_context: Optional[dict]` (fase posterior: influye en ranking, no en clasificación base)

### 2.3 Outputs (contrato canónico NLU)

```json
{
  "status": "ok|fallback|error",
  "intent": "route_planning",
  "confidence": 0.87,
  "entities": {
    "destination": "Museo del Prado",
    "accessibility": "wheelchair",
    "timeframe": "today_evening",
    "transport_preference": "metro"
  },
  "alternatives": [
    {"intent": "event_search", "confidence": 0.42}
  ],
  "provider": "spacy_rule_hybrid",
  "model": "es_core_news_md",
  "language": "es",
  "analysis_version": "nlu_v2"
}
```

### 2.4 Interfaces con el resto del pipeline

- **Accessibility Tool**: consume `entities.destination`, `entities.accessibility`, `intent`.
- **Routes Tool**: consume `destination` normalizado + señales de movilidad/transporte.
- **Tourism Info Tool**: consume `destination` + tipo de intención.
- **LocationNER Tool**: se mantiene como paso especializado de extracción de spans de localización sobre texto crudo.
- **Backend Adapter / API**: expone `intent`, `entities` y trazabilidad en metadata.

### 2.5 Solapamiento NLU vs NER y decisión de arquitectura

**Solapamiento existente:**
- NLU produce `destination` (normalización de negocio).
- NER produce `locations` (extracción de spans LOC/GPE/FAC).

**Recomendación:** **NO fusionar** en esta iteración.

Motivos:
- Responsabilidades distintas: NLU clasifica intención + slots; NER extrae entidades textuales.
- Ritmos de evolución distintos: NER puede cambiar proveedor/modelos sin impactar taxonomía de intent.
- Menor riesgo de regresión y mejor observabilidad por etapa.

**Estrategia recomendada:** mantener tools separadas + añadir un `EntityResolver`/merge policy en Business:
- Priorizar `LocationNER.top_location` para señal geográfica cruda.
- Priorizar NLU para entidad de negocio normalizada (`destination`) y estructura de slots.
- Registrar conflictos NLU/NER en metadata para tuning posterior.

---

## 3) Frameworks, librerías y tecnologías recomendadas

### Opción base recomendada (híbrida, incremental)

- `spaCy` para análisis lingüístico (tokenización, lemas, matcher, entities auxiliares).
- Reglas deterministas de dominio (patterns) para casos críticos y fallback.
- Clasificador ligero opcional (`scikit-learn`) para intent ranking (fase 2/3), entrenable offline.

### Configuración por entorno

Agregar settings `VOICEFLOW_NLU_*` en `integration/configuration/settings.py`:
- `VOICEFLOW_NLU_ENABLED=true`
- `VOICEFLOW_NLU_PROVIDER=spacy_rule_hybrid`
- `VOICEFLOW_NLU_DEFAULT_LANGUAGE=es`
- `VOICEFLOW_NLU_MODEL_MAP={"es":"es_core_news_md","en":"en_core_web_sm"}`
- `VOICEFLOW_NLU_INTENT_MAP={...}`
- `VOICEFLOW_NLU_CONFIDENCE_THRESHOLD=0.60`
- `VOICEFLOW_NLU_FALLBACK_INTENT=general_query`

### Observabilidad mínima

Log estructurado por ejecución NLU:
- `provider`, `model`, `language`, `latency_ms`
- `intent`, `confidence`
- `entity_count`, `status`, `fallback_reason`

---

## 4) Estrategia de commits (5 commits)

## Commit 1 — Contratos NLU + configuración por entorno

**Objetivo**: Introducir interfaz NLU y settings sin integración funcional aún.

### Archivos a crear/modificar

- [ ] Crear `shared/interfaces/nlu_interface.py`
- [ ] Modificar `shared/interfaces/__init__.py`
- [ ] Modificar `integration/configuration/settings.py`
- [ ] Actualizar `.env.example`

### Checklist técnico

- [ ] Definir `NLUServiceInterface`:
  - [ ] `analyze_text(text: str, language: str | None = None, profile_context: dict | None = None) -> dict`
  - [ ] `is_service_available() -> bool`
  - [ ] `get_supported_languages() -> list[str]`
  - [ ] `get_service_info() -> dict`
- [ ] Parseo robusto de mapas JSON (`model_map`, `intent_map`) con fallback seguro.
- [ ] Valores por defecto no disruptivos con API actual.

### Validación mínima del commit

- [ ] `poetry run ruff check shared/ integration/`
- [ ] `poetry run ruff format --check shared/ integration/`

### Mensaje de commit sugerido

`feat(shared,integration): add NLU interface and env-driven NLU settings`

---

## Commit 2 — Proveedor NLU + Factory (Integration)

**Objetivo**: Implementar proveedor NLU desacoplado y factoría extensible.

### Archivos a crear/modificar

- [ ] Crear `integration/external_apis/spacy_nlu_service.py`
- [ ] Crear `integration/external_apis/nlu_factory.py`
- [ ] Modificar `integration/external_apis/__init__.py`
- [ ] (Opcional) Modificar `pyproject.toml` si se incorpora `scikit-learn`

### Checklist técnico

- [ ] Implementar `SpacyNLUService(NLUServiceInterface)`:
  - [ ] extracción de intent + slots en ES/EN (configurable)
  - [ ] confidence score y `alternatives`
  - [ ] fallback a `general_query` con `status=fallback`
- [ ] Implementar `NLUServiceFactory` con registry:
  - [ ] `create_service(provider, **kwargs)`
  - [ ] `create_from_settings(settings)`
  - [ ] `register_service(name, cls)`

### Validación mínima del commit

- [ ] `poetry run ruff check integration/`
- [ ] smoke local de provider y factory con frases ES/EN

### Mensaje de commit sugerido

`feat(integration): implement pluggable NLU provider and factory`

---

## Commit 3 — Refactor TourismNLUTool + merge policy NLU/NER

**Objetivo**: Migrar la tool de negocio para delegar en NLU service y definir resolución NLU+NER.

### Archivos a crear/modificar

- [ ] Modificar `business/domains/tourism/tools/nlu_tool.py`
- [ ] Modificar `business/domains/tourism/tools/__init__.py` (si aplica)
- [ ] Modificar `business/domains/tourism/agent.py`
- [ ] (Opcional) Crear `business/domains/tourism/entity_resolver.py`

### Checklist técnico

- [ ] `TourismNLUTool` delega al servicio NLU (sin acoplamiento de librería concreta).
- [ ] Mantener shape compatible de `intent` y `entities` para tools downstream.
- [ ] Añadir política explícita de reconciliación NLU/NER en metadata.
- [ ] Garantizar continuidad del pipeline si NLU falla (`fallback intent`).

### Validación mínima del commit

- [ ] `poetry run ruff check business/`
- [ ] tests de pipeline: NLU presente + NER presente + metadata coherente

### Mensaje de commit sugerido

`refactor(business): decouple TourismNLUTool and add NLU-NER merge policy`

---

## Commit 4 — Wiring Application/DI + contrato API + docs técnicas

**Objetivo**: Conectar NLU factory al runtime y documentar contrato operativo.

### Archivos a crear/modificar

- [ ] Modificar `shared/utils/dependencies.py`
- [ ] Modificar `application/orchestration/backend_adapter.py`
- [ ] Modificar `documentation/API_REFERENCE.md`
- [ ] Modificar `documentation/design/02_integration_layer_design.md`
- [ ] Modificar `documentation/design/03_business_layer_design.md`
- [ ] Modificar `documentation/DEVELOPMENT.md`

### Checklist técnico

- [ ] Inyección de NLU service vía factory/settings.
- [ ] Exposición opcional de `metadata.tool_outputs.nlu` para trazabilidad estable.
- [ ] Documentar variables `VOICEFLOW_NLU_*` y ejemplos de prueba.
- [ ] Confirmar no-breaking-change del endpoint `/api/v1/chat/message`.

### Validación mínima del commit

- [ ] smoke endpoint chat en modo real/simulado
- [ ] verificación manual de docs alineadas con código

### Mensaje de commit sugerido

`refactor(application,docs): wire NLU service via DI and document runtime contract`

---

## Commit 5 — Tests por capa + hardening

**Objetivo**: Cobertura integral y cierre de criterios de aceptación.

### Archivos a crear/modificar

- [ ] Crear `tests/test_shared/test_nlu_interface.py`
- [ ] Crear `tests/test_integration/test_spacy_nlu_service.py`
- [ ] Crear `tests/test_integration/test_nlu_factory.py`
- [ ] Crear `tests/test_business/test_tourism_nlu_tool.py`
- [ ] Crear `tests/test_business/test_tourism_agent_nlu_ner_merge.py`
- [ ] Crear `tests/test_application/test_chat_nlu_integration.py`
- [ ] Ajustar `tests/conftest.py` si requiere fixtures

### Checklist técnico

- [ ] Unit tests: parseo settings NLU, contrato y schema estable.
- [ ] Integration tests:
  - [ ] clasificación intent ES
  - [ ] clasificación intent EN
  - [ ] fallback cuando provider/modelo falla
  - [ ] endpoint chat mantiene `intent/entities` y metadata esperada
- [ ] Añadir marcas `@pytest.mark.unit` / `@pytest.mark.integration`.

### Validación final del commit

- [ ] `poetry run pytest tests/test_shared/ tests/test_integration/ tests/test_business/ tests/test_application/ -v`
- [ ] `poetry run ruff check .`
- [ ] `poetry run ruff format --check .`
- [ ] `poetry run mypy shared/ integration/ business/ application/`

### Mensaje de commit sugerido

`test: add unit and integration coverage for NLU intent+slots pipeline`

---

## 5) Criterios de aceptación (Definition of Done)

- [ ] NLU produce `intent` y `entities` consistentes en flujo real de chat.
- [ ] Pipeline mantiene convivencia NLU + NER con política de resolución trazable.
- [ ] Configuración de NLU por entorno sin cambios de código cliente.
- [ ] Business/Application sin acoplamiento directo a proveedor NLU.
- [ ] Contrato API compatible con consumidores actuales.
- [ ] Pruebas por capa pasando + lint/formato en verde.
- [ ] Documentación técnica y operativa actualizada.

---

## 6) Riesgos y mitigación

- **Riesgo**: baja precisión de intent en consultas ambiguas/multintent.  
  **Mitigación**: `alternatives` + confidence threshold + fallback controlado.

- **Riesgo**: conflicto entre `destination` de NLU y `top_location` de NER.  
  **Mitigación**: `EntityResolver` con reglas explícitas y logging de conflicto.

- **Riesgo**: regresiones en tools downstream que dependen de shape legacy de NLU.  
  **Mitigación**: mantener backward compatibility + tests de contrato en Business/Application.

- **Riesgo**: incremento de latencia por análisis NLU más rico.  
  **Mitigación**: caché de recursos, métricas `latency_ms`, tuning de modelo por idioma.

---

## 7) Comandos rápidos por commit

```bash
# Validación corta por fase
poetry run ruff check .
poetry run ruff format --check .

# Tests por capas (foco NLU)
poetry run pytest tests/test_shared/ tests/test_integration/ tests/test_business/ tests/test_application/ -v

# Verificación de contrato en API
curl -s -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message":"Quiero una ruta accesible al Museo del Prado"}' | jq '{intent,entities,pipeline_steps,metadata}'
```
