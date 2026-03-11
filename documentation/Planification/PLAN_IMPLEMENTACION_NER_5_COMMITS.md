# Plan de ejecución — Tool NER LOC con spaCy (5 commits)

**Fecha**: 22 de Febrero de 2026  
**Rama**: `feature/implement-user-profile-preferences`  
**Objetivo**: Implementar reconocimiento de localizaciones (LOC) con spaCy, configurable por idioma/modelo sin cambios de código cliente, y desacoplado para sustituir proveedor NER en el futuro.

---

## 1) Alcance y principios de implementación

### Requisitos obligatorios cubiertos

- [ ] Uso de `spacy` + `es_core_news_md` como baseline operativo.
- [ ] Configuración por entorno para modelos `_md` / `_sm` y múltiples idiomas (`es`, `en`, ...), sin modificar código.
- [ ] Abstracción suficiente para reemplazar spaCy por otro framework sin tocar código cliente de Business/Application.
- [ ] Cumplimiento con arquitectura por capas y guías del proyecto (DI/factory, separación de concerns, fallback graceful, testing por capas).

### Restricciones de arquitectura

- Capa `Business` **no** debe importar spaCy directamente.
- Capa `Shared` define contratos; `Integration` implementa proveedores concretos.
- Capa `Application` orquesta wiring/factory, evitando acoplamiento al proveedor específico.
- Mantener compatibilidad hacia atrás del pipeline y de `entities` en respuesta.

---

## 2) Estrategia de commits (5 commits)

## Commit 1 — Contratos + Configuración NER (sin integración funcional)

**Objetivo**: Definir el contrato NER y habilitar configuración flexible por env vars.

### Archivos a crear/modificar

- [ ] Crear `shared/interfaces/ner_interface.py`
- [ ] Modificar `integration/configuration/settings.py`
- [ ] Actualizar `.env.example` (si existe en repo)
- [ ] (Opcional) Ajustar exports `shared/interfaces/__init__.py` si aplica

### Checklist técnico

- [ ] Definir `NERServiceInterface` con métodos mínimos:
  - [ ] `extract_locations(text: str, language: str | None = None) -> dict`
  - [ ] `is_service_available() -> bool`
  - [ ] `get_service_info() -> dict`
- [ ] Añadir settings NER:
  - [ ] `ner_provider` (default: `spacy`)
  - [ ] `ner_enabled` (default: `true`)
  - [ ] `ner_default_language` (default: `es`)
  - [ ] `ner_model_map` (JSON string idioma→modelo; default con `es_core_news_md`)
  - [ ] `ner_fallback_model` (default: `es_core_news_sm`)
  - [ ] `ner_confidence_threshold` (si se usa score)
- [ ] Parsear `ner_model_map` de forma segura (fallback a mapa por defecto).
- [ ] Documentar en comentarios cómo agregar nuevos idiomas/modelos por env.

### Validación mínima del commit

- [ ] `poetry run ruff check .`
- [ ] `poetry run ruff format --check .`
- [ ] `poetry run mypy shared/ integration/`

### Mensaje de commit sugerido

`feat(shared,integration): add NER interface and environment-driven NER settings`

---

## Commit 2 — Implementación proveedor spaCy + Factory NER

**Objetivo**: Implementar adapter spaCy desacoplado y factoría extensible de proveedores NER.

### Archivos a crear/modificar

- [ ] Crear `integration/external_apis/spacy_ner_service.py`
- [ ] Crear `integration/external_apis/ner_factory.py`
- [ ] Modificar `pyproject.toml`
- [ ] (Opcional) Crear script de bootstrap modelos en `tools/` o `docker/scripts/`

### Checklist técnico

- [ ] Implementar `SpacyNERService(NERServiceInterface)`:
  - [ ] Carga lazy por idioma/modelo
  - [ ] Caché de pipelines cargados
  - [ ] Extracción de entidades tipo `LOC`/`GPE`
  - [ ] Respuesta canónica (`locations`, `top_location`, `provider`, `model`, `language`)
- [ ] Manejar errores de carga de modelo sin romper request (degradación graceful).
- [ ] Implementar `NERServiceFactory` con patrón registry:
  - [ ] `create_service(provider, **kwargs)`
  - [ ] `create_from_settings(settings)`
  - [ ] `register_service(name, cls)`
- [ ] Añadir dependencia `spacy` en `pyproject.toml`.
- [ ] Definir procedimiento reproducible para instalar modelos:
  - [ ] `python -m spacy download es_core_news_md`
  - [ ] soporte para `es_core_news_sm` y `en_core_web_sm/md` según `ner_model_map`.

### Validación mínima del commit

- [ ] `poetry lock` (si aplica)
- [ ] `poetry install`
- [ ] `poetry run ruff check .`
- [ ] `poetry run mypy integration/`
- [ ] Prueba manual rápida: instanciación factory + extracción sobre texto español.

### Mensaje de commit sugerido

`feat(integration): implement spaCy NER provider with pluggable factory`

---

## Commit 3 — Tool NER LOC en Business + integración en pipeline

**Objetivo**: Introducir nueva tool de dominio para localización y conectarla al flujo multi-agent.

### Archivos a crear/modificar

- [ ] Crear `business/domains/tourism/tools/location_ner_tool.py`
- [ ] Modificar `business/domains/tourism/tools/__init__.py`
- [ ] Modificar `business/domains/tourism/agent.py`
- [ ] Modificar `business/domains/tourism/prompts/response_prompt.py` (solo si requiere campos nuevos)

### Checklist técnico

- [ ] `LocationNERTool` extiende `BaseTool`, pero delega al servicio NER (sin importar spaCy).
- [ ] Input: texto usuario; Output JSON canónico con localizaciones.
- [ ] Integrar en `_execute_pipeline()`:
  - [ ] Ejecutar NER en etapa temprana (después de NLU o en paralelo lógico secuencial)
  - [ ] Incluir resultado en `tool_results` y `metadata`
  - [ ] Añadir `pipeline_steps` para trazabilidad
- [ ] Mantener compatibilidad:
  - [ ] Si NER falla, no abortar pipeline
  - [ ] Fallback a extracción previa/hardcoded para no romper comportamiento actual
- [ ] Alinear `entities` finales para API existente (`location`, etc.).

### Validación mínima del commit

- [ ] `poetry run ruff check business/`
- [ ] `poetry run mypy business/`
- [ ] Smoke test local: query con ciudad/lugar devuelve `entities.location` consistente.

### Mensaje de commit sugerido

`feat(business): add location NER tool and wire it into tourism pipeline`

---

## Commit 4 — Wiring Application/DI + observabilidad + documentación técnica

**Objetivo**: Conectar factory NER al runtime de la app y documentar configuración operativa.

### Archivos a crear/modificar

- [ ] Modificar `application/orchestration/backend_adapter.py` (si requiere inyección de servicio/contexto)
- [ ] Modificar `shared/utils/dependencies.py` o punto de wiring vigente
- [ ] Modificar `documentation/API_REFERENCE.md` (si cambia shape de `entities` o pipeline)
- [ ] Modificar `documentation/design/02_integration_layer_design.md`
- [ ] Modificar `documentation/design/03_business_layer_design.md`
- [ ] Modificar `documentation/DEVELOPMENT.md` (setup modelos spaCy)

### Checklist técnico

- [ ] Inyección de servicio NER vía factory/settings (sin acoplar Business a spaCy).
- [ ] Logging estructurado para NER:
  - [ ] provider, model, language, latency_ms
  - [ ] cantidad de LOC detectadas
- [ ] Documentar configuración por env con ejemplos:
  - [ ] `VOICEFLOW_NER_PROVIDER=spacy`
  - [ ] `VOICEFLOW_NER_DEFAULT_LANGUAGE=es`
  - [ ] `VOICEFLOW_NER_MODEL_MAP={"es":"es_core_news_md","en":"en_core_web_sm"}`
- [ ] Garantizar que API no rompe consumidores actuales.

### Validación mínima del commit

- [ ] `poetry run ruff check .`
- [ ] Revisión manual de docs coherentes con código actual.
- [ ] Smoke de endpoint `/api/v1/chat/message` en modo simulado/real según disponibilidad.

### Mensaje de commit sugerido

`refactor(application,docs): wire NER service via DI and document runtime configuration`

---

## Commit 5 — Tests unitarios + integración + hardening

**Objetivo**: Cubrir la implementación con pruebas por capa y cerrar criterios de aceptación.

### Archivos a crear/modificar

- [ ] Crear `tests/test_shared/test_ner_interface.py`
- [ ] Crear `tests/test_integration/test_spacy_ner_service.py`
- [ ] Crear `tests/test_integration/test_ner_factory.py`
- [ ] Crear `tests/test_business/test_location_ner_tool.py`
- [ ] Crear `tests/test_business/test_tourism_agent_ner_pipeline.py`
- [ ] Crear `tests/test_application/test_chat_ner_integration.py`
- [ ] Ajustar `tests/conftest.py` si requiere fixtures nuevas

### Checklist técnico

- [ ] Unit tests (sin red):
  - [ ] Parsing settings NER
  - [ ] Factory provider resolution
  - [ ] Tool output schema estable
- [ ] Integration tests:
  - [ ] spaCy detecta LOC para ES (`Madrid`, `Sevilla`, etc.)
  - [ ] soporte idioma EN según `ner_model_map`
  - [ ] fallback cuando modelo no está disponible
  - [ ] endpoint chat incorpora entidades sin romper contrato
- [ ] Añadir marcas `@pytest.mark.unit` / `@pytest.mark.integration`.
- [ ] Cobertura mínima en módulos nuevos/afectados.

### Validación final del commit

- [ ] `poetry run pytest tests/test_shared/ tests/test_integration/ tests/test_business/ tests/test_application/ -v`
- [ ] `poetry run ruff check .`
- [ ] `poetry run ruff format --check .`
- [ ] `poetry run mypy application/ business/ shared/ integration/`

### Mensaje de commit sugerido

`test: add unit and integration coverage for configurable NER LOC pipeline`

---

## 3) Orden de ejecución recomendado

1. Commit 1 (contratos + settings)
2. Commit 2 (proveedor spaCy + factory)
3. Commit 3 (tool NER + pipeline)
4. Commit 4 (wiring app + docs)
5. Commit 5 (tests + hardening)

---

## 4) Checklist global de salida (Definition of Done)

- [ ] NER LOC funcionando en flujo de chat.
- [ ] Configuración idioma/modelo vía env sin cambios de código.
- [ ] Cambio de proveedor NER posible implementando nuevo adapter en Integration + registro en factory.
- [ ] Business y Application sin dependencias directas a spaCy.
- [ ] Contrato API vigente compatible.
- [ ] Tests unitarios e integración pasando.
- [ ] Lint/formato/tipos en verde.
- [ ] Documentación actualizada y coherente.

---

## 5) Riesgos y mitigación

- **Riesgo**: modelo spaCy no instalado en runtime.  
  **Mitigación**: fallback `_md -> _sm` + mensaje de health/log claro.

- **Riesgo**: cambios en pipeline afecten tools downstream.  
  **Mitigación**: mantener schema de `entities` y fallback a flujo actual si NER falla.

- **Riesgo**: acoplamiento accidental a spaCy en Business.  
  **Mitigación**: revisión de imports por capa + tests de contrato/factory.

- **Riesgo**: latencia adicional en NER.  
  **Mitigación**: carga lazy + caché de modelos + métrica `duration_ms` por tool.

---

## 6) Comandos rápidos por commit

```bash
# Validación corta en cada commit
poetry run ruff check .
poetry run ruff format --check .

# Validación por fase (según módulos tocados)
poetry run mypy shared/ integration/
poetry run mypy business/
poetry run mypy application/

# Test suite final
poetry run pytest tests/ -v
```
