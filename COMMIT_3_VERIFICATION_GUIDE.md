## Commit 3 Verification & Testing Guide

### Overview
Commit 3 implementa la **LocationNERTool** que extrae entidades de localización del texto del usuario usando NER (spaCy). La herramienta se puede probar en 3 niveles: unitario, integración, e end-to-end con Docker.

---

### Level 1: Unit Tests

Ejecuta solo los tests unitarios de `LocationNERTool`:

```bash
cd /home/alex/Documentos/Code/voiceFlowPOC
poetry run pytest tests/test_business/test_location_ner_tool.py -v
```

**Expected Output:**
```
======================== 8 passed in X.XXs ========================
```

**What it validates:**
- ✅ Instanciación correcta de la tool
- ✅ Respuesta JSON cuando el servicio NER no está disponible
- ✅ Extracción exitosa de localizaciones cuando spaCy está disponible
- ✅ Manejo de input vacío
- ✅ Manejo de errores graceful
- ✅ Parámetro de idioma se pasa correctamente
- ✅ Versión async funciona

---

### Level 2: Integration Tests (Pipeline)

Ejecuta tests que validan que LocationNER se integra en el pipeline del agente:

```bash
cd /home/alex/Documentos/Code/voiceFlowPOC
poetry run pytest tests/test_business/test_tourism_agent_ner_pipeline.py -v
```

**Expected Output:**
```
======================== 5 passed in X.XXs ========================
```

**What it validates:**
- ✅ LocationNERTool está inicializado en `TourismMultiAgent`
- ✅ LocationNER se ejecuta en el pipeline (tool_results contiene la clave)
- ✅ LocationNER ejecuta **después** de NLU en el pipeline (order correcto)
- ✅ Pipeline continúa exitosamente si NER no está disponible (fallback)
- ✅ Resultado NER es parseado y agregado a metadata

---

### Level 3: End-to-End with Docker

#### A. Build Docker image (con mitigaciones para timeouts)

```bash
cd /home/alex/Documentos/Code/voiceFlowPOC
docker compose build --no-cache
```

**Timeout mitigations (ya aplicadas en Dockerfile):**
- `PIP_DEFAULT_TIMEOUT=300` (5 min para descargas de wheels)
- `PIP_RETRIES=10` (reintentos para descargas fallidas)
- `poetry max-workers=4` (limita paralelismo)
- Torch CPU-only (evita descargas de nvidia-wheels)
- Modelo spaCy `es_core_news_md` incluido en build

**Logs esperados:**
```
...
Step 8/X : RUN poetry config installer.max-workers 4
...
Successfully built <image-id>
```

Si el build falla con `ReadTimeoutError`:
- Aumentar `PIP_DEFAULT_TIMEOUT` a 600+ en Dockerfile
- Checar conectividad de red: `python -m pip index versions spacy`

---

#### B. Smoke test rápido en container

Una vez que la imagen está construida:

```bash
docker compose run --rm app python -m pytest tests/test_integration/ner_integration_smoke.py -v -s
```

**Expected Output:**
```
NER Smoke Test: Extracting locations from "Quiero visitar el Palacio Real"
Extracted locations: [{"name": "Palacio Real", "type": "LOC"}, ...]
===== test session starts =====
PASSED
```

Si spaCy no está disponible (esperado en máquinas sin modelo):
```
NER service not available (model not found), skipping extraction
===== test session starts =====
PASSED (no-op test)
```

---

### Level 4: Full API Integration (Optional)

Si el resto del stack está levantado (OpenAI key, etc.):

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "message": "¿Cuál es la accesibilidad del Palacio Real?",
    "domain": "tourism"
  }'
```

**Expected Response:**
- El JSON de respuesta debe incluir un bloque `metadata.pipeline_steps` con un paso `LocationNER`
- En `metadata.tool_results_parsed.locationner` (o `location_ner`), debe haber un array `locations` con las entidades extraídas de "Palacio Real"

---

### Commit 3 Artifacts

#### Files Created:
1. **`business/domains/tourism/tools/location_ner_tool.py`** (130 líneas)
   - Clase `LocationNERTool` que extiende `langchain.BaseTool`
   - Métodos `_run()` (sync) y `_arun()` (async)
   - Delega a `NERServiceFactory` de Integration layer
   - Output JSON: `{"locations": [...], "top_location": str|None, "provider": "spacy", "model": str, "language": str, "status": "ok"|"error"|"unavailable"}`

2. **`tests/test_business/test_location_ner_tool.py`** (160 líneas)
   - 8 tests unitarios (mocking NER service)
   - Cobertura: success path, unavailable service, empty input, error handling, async

3. **`tests/test_business/test_tourism_agent_ner_pipeline.py`** (180 líneas)
   - 5 tests de integración para pipeline
   - Valida orden, fallback, metadata parsing

#### Files Modified:
1. **`business/domains/tourism/agent.py`**
   - Importar: `from business.domains.tourism.tools.location_ner_tool import LocationNERTool`
   - Init: `self.location_ner = LocationNERTool()`
   - Pipeline: agregado `run_tool("LocationNER", self.location_ner, nlu_raw)` después de NLU
   - Type hint: `_execute_pipeline()` return type corregido a `tuple[dict[str, str], dict]`

---

### Verification Checklist

- [ ] `poetry run ruff check business/domains/tourism/tools/location_ner_tool.py` → All checks passed
- [ ] `poetry run pytest tests/test_business/test_location_ner_tool.py -v` → 8 passed
- [ ] `poetry run pytest tests/test_business/test_tourism_agent_ner_pipeline.py -v` → 5 passed
- [ ] `docker compose build --no-cache` → Successfully built (timeout-resilient)
- [ ] `docker compose run --rm app poetry run pytest tests/test_integration/ner_integration_smoke.py -v` → PASSED or no-op PASSED

---

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `spacy model not found` in tests | Normal — spaCy models download in Docker build phase. Locally, NER service returns "unavailable" gracefully. |
| Docker build timeout on torch | Aumentar `PIP_DEFAULT_TIMEOUT` a 600 en Dockerfile; Dockerfile ya incluye mitigación. |
| Test warnings about coroutines | Esperado — AsyncMock en tests unitarios genera RuntimeWarning. No afecta test results. |
| mypy errors on agent.py:40 | Pre-existente (langchain ChatOpenAI signature deprecated). No es introducido por Commit 3. |
| `LocationNER` not in pipeline_steps | Revisar que se ejecutó `run_tool()` en `_execute_pipeline()`. Checar imports. |

---

### Next: Commit 4

Después de validar Commit 3, el siguiente paso es **Commit 4**: 
- Wiring en Application layer (dependency injection)
- Exposición de settings de NER en configuración
- Documentación

Ver: `PLAN_IMPLEMENTACION_NER_5_COMMITS.md` (Commit 4 section)
