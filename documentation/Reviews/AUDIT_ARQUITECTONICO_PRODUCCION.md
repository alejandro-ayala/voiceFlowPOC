# Auditoría Arquitectónica Completa — VoiceFlow Tourism Multi-Agent System

**Fecha:** 03 Marzo 2026
**Auditor:** Principal Software Architect (AI Systems & Distributed Architecture)
**Rama auditada:** `audit/real-tools-implementation`
**Alcance:** Revisión full-stack del sistema para definir ruta a producción
**Archivos revisados:** 65+ archivos fuente, 17 tests, 8 archivos de configuración

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Estado Arquitectónico por Capa](#2-estado-arquitectónico-por-capa)
3. [Análisis del Pipeline de Orquestación](#3-análisis-del-pipeline-de-orquestación)
4. [Análisis de Tools — Foundation vs Domain](#4-análisis-de-tools--foundation-vs-domain)
5. [Sistema de Perfiles](#5-sistema-de-perfiles)
6. [Modelo de Concurrencia y Async](#6-modelo-de-concurrencia-y-async)
7. [Contrato API y Flujo Frontend-Backend](#7-contrato-api-y-flujo-frontend-backend)
8. [Gestión de Sesiones y Estado](#8-gestión-de-sesiones-y-estado)
9. [Cobertura de Tests](#9-cobertura-de-tests)
10. [Seguridad](#10-seguridad)
11. [Infraestructura Docker y CI/CD](#11-infraestructura-docker-y-cicd)
12. [Observabilidad y Operaciones](#12-observabilidad-y-operaciones)
13. [Evaluación Consolidada](#13-evaluación-consolidada)
14. [Plan de Implementación — Ruta a Producción](#14-plan-de-implementación--ruta-a-producción)
15. [Riesgos y Mitigaciones](#15-riesgos-y-mitigaciones)
16. [Análisis de APIs, Frameworks y Enfoque RAG para Tools Reales](#16-análisis-de-apis-frameworks-y-enfoque-rag-para-tools-reales)

---

## 1. Resumen Ejecutivo

### Diagnóstico

VoiceFlow es un **prototipo arquitectónico funcional** con una base sólida en separación de capas, inyección de dependencias y patrón factory para providers. El NLU (OpenAI function-calling + keyword fallback) y el NER (spaCy) son robustos y production-grade.

Sin embargo, **el sistema no está preparado para producción** por 4 bloqueadores:

| # | Bloqueador | Impacto |
|---|---|---|
| B1 | Tools de dominio son stubs con datos mock hardcodeados | El LLM ignora las tools y usa conocimiento preentrenado — los datos estructurados (`tourism_data`) son irrelevantes o null |
| B2 | `asyncio.run()` anidado dentro de event loop existente | Bug latente que impide streaming, WebSockets y background tasks |
| B3 | Sin contratos tipados entre tools | El encadenamiento inter-tool usa string parsing heurístico (`if "Prado" in text`) que se romperá al integrar APIs reales |
| B4 | Sin autenticación, rate limiting ni HTTPS | Cualquier endpoint es accesible sin restricción |

### Evaluación Global

| Área | Puntuación | Tendencia |
|---|---|---|
| Arquitectura de capas | **7.5/10** | Sólida, deuda técnica menor |
| Foundation Tools (NLU+NER) | **8/10** | Production-ready |
| Domain Tools | **2/10** | Stubs — reescritura necesaria |
| Orquestación | **4/10** | Pipeline rígido sin gestión de errores |
| API Contract | **6/10** | Parcialmente estable, inconsistencias en responses |
| Seguridad | **2/10** | No existe (auth=0, rate-limit=0, HTTPS=0) |
| Testing | **6/10** | Buen coverage NLU/NER, gaps en orchestrator y e2e |
| Infraestructura | **5/10** | Docker funcional, CI básico, producción no hardened |
| Observabilidad | **3/10** | structlog presente pero sin correlation ID, métricas ni alertas |
| **PRODUCCIÓN-READINESS** | **3.5/10** | **No listo** |

---

## 2. Estado Arquitectónico por Capa

### 2.1 Shared Layer (`shared/`)

**Estado: Sólido**

```
shared/
├── interfaces/     → 5 ABCs (Audio, Backend, Conversation, Auth, Storage) + NLU + NER
├── models/         → NLUResult, NLUEntitySet, ResolvedEntities (Pydantic v2)
├── exceptions/     → Jerarquía VoiceFlowException → 5 subtipos
└── utils/          → DI container (FastAPI Depends)
```

**Fortalezas:**
- Interfaces bien segregadas (ISP)
- Modelos Pydantic con validación estricta (confidence 0-1, status literals)
- Factory pattern con registry dinámico (`NLUServiceFactory.register_service()`)
- `EntityResolver` con reglas determinísticas bien testeadas (7 tests)

**Hallazgos:**

| ID | Severidad | Archivo | Hallazgo |
|---|---|---|---|
| S-01 | Baja | `dependencies.py:77-105` | `initialize_services()` usa globals mutables (`_backend_service`, etc.) en lugar de lifecycle hooks de FastAPI. `cleanup_services()` tiene cuerpo vacío — nunca limpia recursos |
| S-02 | Baja | `dependencies.py:131-163` | `SimulatedAudioService` definido en módulo de DI en lugar de en integration layer. Viola SRP |
| S-03 | Media | `interfaces.py` | `AuthInterface` y `StorageInterface` definidos pero sin ninguna implementación en todo el proyecto. Son dead code |

### 2.2 Integration Layer (`integration/`)

**Estado: Funcional con gaps**

```
integration/
├── configuration/settings.py     → 48 settings via pydantic-settings
├── external_apis/
│   ├── openai_nlu_service.py    → Function-calling con gpt-4o-mini
│   ├── keyword_nlu_service.py   → Fallback por patrones
│   ├── spacy_ner_service.py     → es_core_news_md con fallback de modelo
│   ├── nlu_factory.py           → Registry pattern (openai, keyword)
│   ├── ner_factory.py           → Registry pattern (spacy)
│   ├── stt_factory.py           → Registry pattern (azure, whisper_local, whisper_api)
│   ├── azure_stt_client.py      → Azure Speech SDK
│   └── whisper_services.py      → Local + API whisper
└── data_persistence/
    └── conversation_repository.py → In-memory dict
```

**Fortalezas:**
- Patrón factory con fallback chain (si OpenAI falla → keyword)
- spaCy NER con resolución dinámica de modelo por idioma
- Settings centralizados con `env_prefix="VOICEFLOW_"` y validación Pydantic

**Hallazgos:**

| ID | Severidad | Archivo | Hallazgo |
|---|---|---|---|
| I-01 | Alta | `settings.py:180` | Singleton global `settings = Settings()` se instancia al importar el módulo. Si `.env` no existe en ese momento, usa defaults silenciosamente. Dificulta testing y configuración dinámica |
| I-02 | Media | `openai_nlu_service.py` | `profile_context` se acepta en signature pero se elimina explícitamente (`del profile_context`). Interfaz promete funcionalidad que no existe |
| I-03 | Media | `settings.py:52-54` | Modelo LLM para síntesis (`gpt-4`) hardcodeado en `agent.py`, no en Settings. El NLU usa `nlu_openai_model` configurable pero el LLM principal no |
| I-04 | Baja | `conversation_repository.py` | Persistencia in-memory sin TTL. Los datos se pierden al reiniciar |
| I-05 | **Crítica** | Ausente | **No existe capa de resiliencia para APIs externas**: sin rate limiter, sin circuit breaker, sin retry con backoff, sin budget tracking |

### 2.3 Business Layer (`business/`)

**Estado: Framework sólido, dominio stub**

```
business/
├── core/
│   ├── orchestrator.py          → Template Method pattern (abstracto)
│   ├── interfaces.py            → MultiAgentInterface (ABC)
│   ├── models.py                → AgentResponse dataclass
│   └── canonicalizer.py         → Normalización ES→EN para UI
└── domains/tourism/
    ├── agent.py                 → TourismMultiAgent (356 líneas, el corazón)
    ├── entity_resolver.py       → Merge NLU+NER determinístico
    ├── tools/                   → 5 tools (2 reales, 3 stubs)
    ├── data/                    → Diccionarios Python mock
    └── prompts/                 → System + Response prompts
```

**Hallazgos detallados en secciones 3, 4 y 6.**

### 2.4 Application Layer (`application/`)

**Estado: Correcto con inconsistencias en responses**

```
application/
├── api/v1/
│   ├── chat.py        → 7 endpoints (message, conversations, demos)
│   ├── audio.py       → 4 endpoints (transcribe, validate, stream-config)
│   └── health.py      → 3 endpoints (general, backend, audio)
├── models/
│   ├── requests.py    → 7 modelos Pydantic de request
│   └── responses.py   → 14 modelos Pydantic de response
├── orchestration/
│   └── backend_adapter.py → 450+ líneas, adapta business → API
└── services/
    ├── audio_service.py
    ├── conversation_service.py
    └── profile_service.py
```

**Hallazgos:**

| ID | Severidad | Archivo | Hallazgo |
|---|---|---|---|
| A-01 | Media | `responses.py:13-19` | `PipelineStatus` hereda de `str` pero no es un `Enum`. Usa constantes de clase como atributos de instancia — patrón inusual que puede confundir |
| A-02 | Media | `responses.py:98-108` | Validator de `PipelineStep.status` hace whitelist silenciosa — status inválido se convierte en `"pending"` sin log ni warning |
| A-03 | Media | `chat.py` + `audio.py` | Endpoints de demo y delete devuelven `dict` crudo en lugar de modelos Pydantic tipados. 5 de 14 endpoints no usan response models |
| A-04 | Baja | `backend_adapter.py` | Archivo de 450+ líneas con múltiples responsabilidades: resolución de perfiles, normalización de metadata, modo simulación, shadow mode NLU. Viola SRP |
| A-05 | Media | `audio.py:62-75` | Transcripción fallida retorna HTTP 200 con texto simulado. Frontend no puede distinguir transcripción real de fallback |

### 2.5 Presentation Layer (`presentation/`)

**Estado: Funcional para PoC**

```
presentation/
├── fastapi_factory.py   → App factory con lifecycle hooks
├── server_launcher.py   → Entry point CLI
├── static/js/           → 7 módulos JS (vanilla + Bootstrap 5)
└── templates/           → 3 templates Jinja2
```

**Hallazgos:**

| ID | Severidad | Archivo | Hallazgo |
|---|---|---|---|
| P-01 | Baja | `chat.js:34-36` | `conversationId` generado con `Math.random()` — no criptográficamente seguro. Si se implementa auth, permite colisiones predecibles |
| P-02 | Baja | `app.js` | Sin manejo de errores de red (fetch sin timeout, sin retry) |
| P-03 | Info | `pipeline.js` | Correctamente usa `:scope >` para selectores directos (bug anterior documentado y corregido) |

---

## 3. Análisis del Pipeline de Orquestación

### 3.1 Flujo Actual

```
┌─────────────────────────────────────────────────────────────┐
│  TourismMultiAgent._execute_pipeline()  [agent.py:69-356]   │
│                                                              │
│  1. NLU + NER ───────────────── asyncio.run(gather())       │
│         │                            │                       │
│         ▼                            ▼                       │
│    TourismNLUTool              LocationNERTool               │
│    (OpenAI/keyword)            (spaCy es_core_news_md)       │
│         │                            │                       │
│         └──────────┬─────────────────┘                       │
│                    ▼                                         │
│            EntityResolver.resolve()                          │
│                    │                                         │
│  2. ──────────────▼─────────────── secuencial fijo          │
│    AccessibilityTool(nlu_raw)    ← STUB: lookup en dict     │
│         │                                                    │
│  3. ──▼────────────────────────────────────────             │
│    RoutePlanningTool(accessibility_raw)  ← STUB: lookup      │
│                                                              │
│  4. ──────────────────────────────────────────              │
│    TourismInfoTool(nlu_raw)      ← STUB: lookup en dict     │
│                                                              │
│  5. Canonicalize → Build metadata                            │
│                    │                                         │
│  6. ──────────────▼─── (en orchestrator base)               │
│    LLM Synthesis (gpt-4, temp=0.3, max_tokens=2500)         │
│         │                                                    │
│  7. _extract_structured_data() → regex JSON del LLM         │
│         │                                                    │
│  8. ──▼─── ChatResponse → Frontend                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Problemas Estructurales del Pipeline

#### P-01: Encadenamiento por posición, no por dato (CRÍTICO)

```python
# agent.py:287-295
nlu_raw = tool_results.get("nlu") or ""
run_tool("Accessibility", self.accessibility, nlu_raw)        # ← recibe string NLU
accessibility_raw = tool_results.get("accessibility") or ""
run_tool("Routes", self.route, accessibility_raw)             # ← recibe string Accessibility
run_tool("Venue Info", self.tourism_info, nlu_raw)            # ← recibe string NLU
```

Cada tool recibe un **string JSON** del tool anterior. El parsing es heurístico:

```python
# route_planning_tool.py:50-62
@staticmethod
def _extract_destination(accessibility_info: str) -> str:
    destination = "Madrid centro"            # default hardcoded
    if "Prado" in accessibility_info:        # string matching
        destination = "Museo del Prado"
    elif "Reina" in accessibility_info:
        destination = "Museo Reina Sofía"
    ...
```

**Impacto:** Cuando `AccessibilityTool` devuelva datos reales de Google Places (JSON con `place_id`, `formatted_address`, `wheelchair_accessible_entrance`), este parsing se romperá completamente. No es un problema de "cambiar la fuente de datos" — es un **rediseño de contratos**.

#### P-02: Todas las tools se ejecutan siempre (MEDIO)

No hay routing por intent. Una consulta tipo "¿Qué hora es?" ejecuta NLU + NER + Accessibility + Routes + TourismInfo + LLM. Para queries generales, 3 tools de dominio ejecutan innecesariamente y devuelven datos mock irrelevantes que el LLM ignora.

**Coste:** ~200-400ms extra de latencia + tokens de prompt desperdiciados.

#### P-03: Sin gestión de errores parciales (ALTO)

```python
# Si accessibility falla, el pipeline continúa con string vacío
accessibility_raw = tool_results.get("accessibility") or ""
run_tool("Routes", self.route, accessibility_raw)
# Routes recibe "" → devuelve DEFAULT_ROUTE (Madrid centro genérico)
```

No hay:
- Circuit breaker (si Google Places tiene rate limit, seguimos llamando)
- Retry con backoff
- Degradación parcial documentada (qué pasa si falla la tool X)
- Estado del pipeline que registre qué tools fallaron

#### P-04: Dependencia invertida en datos estructurados (MEDIO)

`_extract_structured_data()` en `agent.py:371-415` implementa una lógica de merge donde los datos del LLM **reemplazan** los datos de las tools si estos parecen genéricos:

```python
is_default = (
    existing_venue.get("accessibility_score") == 6.0        # score genérico
    or existing_venue.get("name", "").startswith("Gu")      # "Guía general"
    or not existing_venue.get("name")
)
if is_default:
    metadata["tourism_data"] = llm_tourism_data             # prefiere LLM
```

Esto significa que el sistema **confía más en la alucinación del LLM que en sus propias tools**. En un sistema con tools reales, esta lógica debe invertirse: los datos de las tools son ground truth, el LLM solo sintetiza texto.

#### P-05: Duplicación de código (BAJO)

`run_tool()` y `record_tool()` en `agent.py:89-220` son funciones internas con ~60% de código duplicado. Ambas hacen JSON parsing, summary heuristics, pipeline_steps append y observability logging para LocationNER.

### 3.3 Métricas del Pipeline Actual

| Paso | Latencia Típica | Fuente | Paralelizable |
|---|---|---|---|
| NLU (OpenAI) | 200-800ms | API call | ✅ (ya paralelo con NER) |
| NER (spaCy) | 5-50ms | Local | ✅ (ya paralelo con NLU) |
| Accessibility | <1ms | Dict lookup | No (depende de NLU) |
| Routes | <1ms | Dict lookup | Sí (independiente de Accessibility) |
| TourismInfo | <1ms | Dict lookup | Sí (independiente) |
| LLM Synthesis | 1000-3000ms | API call (gpt-4) | No (último paso) |
| **Total** | **~1.5-4s** | | |

**Con APIs reales (estimado):**

| Paso | Latencia Estimada |
|---|---|
| NLU (OpenAI) | 200-800ms |
| NER (spaCy) | 5-50ms |
| PlacesSearch (Google) | 200-500ms |
| AccessibilityEnrich (Google) | 100-300ms |
| Directions (Google) | 200-500ms |
| LLM Synthesis | 1000-3000ms |
| **Total** | **~2-5s** (con paralelización) a **~4-8s** (secuencial) |

---

## 4. Análisis de Tools — Foundation vs Domain

### 4.1 Foundation Tools (Production-Ready)

#### TourismNLUTool

| Aspecto | Estado |
|---|---|
| Provider | OpenAI function-calling (`gpt-4o-mini`) + keyword fallback |
| Contrato | `NLUResult` Pydantic con 12 campos tipados |
| Intents | 5: `route_planning`, `event_search`, `restaurant_search`, `accommodation_search`, `general_query` |
| Entidades | `destination`, `accessibility`, `timeframe`, `transport_preference`, `budget` |
| Fallback | Keyword patterns (70% accuracy en corpus de 80 muestras) |
| Shadow mode | Disponible (configurable via `NLU_SHADOW_MODE`) |
| Tests | 3 unit + corpus evaluation (70% keyword, 90% OpenAI) |

**Veredicto:** Sólido. Listo para producción con la cadena de fallback actual.

#### LocationNERTool

| Aspecto | Estado |
|---|---|
| Provider | spaCy `es_core_news_md` con fallback a `es_core_news_sm` |
| Entidades | `LOC`, `GPE`, `FAC` → locations + top_location |
| Idiomas | ES (default), EN (configurable via model_map) |
| Contrato | Dict con `locations`, `top_location`, `provider`, `model`, `status` |
| Tests | 8 tests (unit + integration + error paths) |

**Veredicto:** Sólido. Funcional y bien testeado.

#### EntityResolver

| Aspecto | Estado |
|---|---|
| Lógica | Merge determinístico NLU + NER con 6 reglas de prioridad |
| Output | `ResolvedEntities` Pydantic con `resolution_source` y `conflicts` |
| Tests | 7 tests cubriendo todos los casos de merge |

**Veredicto:** Excelente. Pieza clave bien diseñada.

### 4.2 Domain Tools (STUBS — Reescritura Necesaria)

#### AccessibilityAnalysisTool

```python
# accessibility_tool.py - Toda la lógica:
venue_data = ACCESSIBILITY_DB.get(destination, DEFAULT_ACCESSIBILITY)
```

| Aspecto | Estado |
|---|---|
| Fuente de datos | `ACCESSIBILITY_DB`: 4 venues hardcodeados |
| Parsing de input | `json.loads(nlu_result).entities.destination` — asume formato NLU |
| Fallback | `DEFAULT_ACCESSIBILITY` con score 6.0, "not_certified" |
| Profile-aware | NO — no recibe ni usa profile_context |
| Tests | NINGUNO directo (solo indirecto via pipeline) |

**Datos disponibles (total):**
- Museo del Prado (score 9.2)
- Museo Reina Sofía (score 8.8)
- Espacios musicales Madrid (score 7.5)
- Restaurantes Madrid (score 6.5)

#### RoutePlanningTool

```python
# route_planning_tool.py - Parsing de input:
if "Prado" in accessibility_info:
    destination = "Museo del Prado"
# Solo 4 rutas predefinidas desde "Sol" a 3 destinos
```

| Aspecto | Estado |
|---|---|
| Fuente de datos | `ROUTE_DB`: 3 destinos con rutas fijas |
| Parsing de input | `if "Prado" in text` — string matching literal |
| Siempre asume origen | "Sol Metro Station" — no configurable |
| Profile-aware | NO |
| Tests | NINGUNO |

#### TourismInfoTool

```python
# tourism_info_tool.py - Parsing de input:
if "prado" in venue_lower:
    return "Museo del Prado"
# Solo 6 venues reconocidos
```

| Aspecto | Estado |
|---|---|
| Fuente de datos | `VENUE_DB`: 4 venues con horarios/precios mock |
| Parsing de input | `if "prado" in text.lower()` — substring matching |
| Datos | Horarios semi-ficticios, precios aproximados |
| Profile-aware | NO |
| Tests | NINGUNO |

### 4.3 Impacto Real de los Stubs

**Escenario: "Quiero visitar la Alhambra en Granada"**

| Tool | Input | Output | Útil? |
|---|---|---|---|
| NLU | texto completo | intent=`event_search`, destination=`general` | Parcial (no reconoce Alhambra) |
| NER | texto completo | locations=`["Granada", "Alhambra"]` | ✅ SÍ |
| Accessibility | `"general"` | DEFAULT_ACCESSIBILITY (score 6.0) | ❌ NO — datos de Madrid |
| Routes | `""` | DEFAULT_ROUTE (Metro Madrid) | ❌ NO — rutas de Madrid |
| TourismInfo | `"general"` | DEFAULT_VENUE (horarios genéricos) | ❌ NO |
| LLM | todo lo anterior | Responde usando conocimiento propio | ✅ pero sin datos verificables |

**Resultado:** El sistema produce una respuesta coherente **a pesar** de las tools, no gracias a ellas.

---

## 5. Sistema de Perfiles

### 5.1 Estado Actual

```
┌─ Frontend ─────────────────────────────────────────────────┐
│ ProfileManager carga profiles.json (5 perfiles)            │
│ UI muestra selector → envía active_profile_id en request   │
└──────────────┬─────────────────────────────────────────────┘
               │ {active_profile_id: "night_leisure"}
               ▼
┌─ Application ──────────────────────────────────────────────┐
│ backend_adapter.py:                                         │
│   ProfileService.resolve_profile(id) → profile_context     │
│   profile_context = {                                       │
│     label: "Ocio Nocturno",                                 │
│     prompt_directives: ["Prioriza bares...", ...],          │
│     ranking_bias: {venue_types: {bar: 1.3, club: 1.2, ...}}│
│   }                                                         │
└──────────────┬─────────────────────────────────────────────┘
               │ profile_context
               ▼
┌─ Business ─────────────────────────────────────────────────┐
│ agent.py:                                                   │
│   self._current_profile_context = profile_context  ← STORED│
│   ... tools ejecutan SIN profile_context ...       ← UNUSED│
│   _build_response_prompt(profile_context=...)      ← TONO  │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Qué funciona

1. **Infraestructura completa**: profiles.json → ProfileService → backend_adapter → agent
2. **Prompt injection**: Las directivas del perfil se inyectan en el prompt del LLM
3. **ranking_bias definido**: Cada perfil tiene pesos por tipo de venue (bar: 1.3x, museum: 0.8x, etc.)

### 5.3 Qué NO funciona

| Aspecto | Estado | Detalle |
|---|---|---|
| Tools reciben profile_context | ❌ | `self._current_profile_context` se almacena pero ninguna tool lo lee |
| Ranking de venues por perfil | ❌ | `ranking_bias.venue_types` definido pero nunca aplicado |
| Filtrado por perfil | ❌ | No existe lógica de filtrado |
| NLU considera perfil | ❌ | `openai_nlu_service.py` hace `del profile_context` |
| Datos afectados por perfil | ❌ | Stubs devuelven siempre los mismos datos |

### 5.4 Perfiles Definidos

| ID | Label | Directives (resumen) | ranking_bias highlight |
|---|---|---|---|
| `day_leisure` | Ocio diurno | Planes diurnos, familiares | market: 1.2, park: 1.15 |
| `night_leisure` | Ocio nocturno | Bares, clubes, horarios nocturnos | bar: 1.3, club: 1.2 |
| `dining` | Gastronomía | Restaurantes, variedad culinaria | restaurant: 1.4, cafe: 1.2 |
| `tourism` | Turismo | Monumentos, museos, landmarks | museum: 1.3, landmark: 1.25 |
| `cultural` | Cultural | Exposiciones, teatro, eventos | theater: 1.3, gallery: 1.2 |

**Conclusión:** El perfil es actualmente **cosmético** — solo afecta el tono del texto generado, no los datos ni las recomendaciones. Los pesos de ranking existen pero no se aplican.

---

## 6. Modelo de Concurrencia y Async

### 6.1 Flujo de Ejecución Actual

```
FastAPI (uvicorn) — event loop principal
    │
    ▼ POST /api/v1/chat/message (async handler)
    │
    ▼ backend_adapter.process_query() → async
    │
    ▼ agent.process_request() → async
    │
    ▼ asyncio.to_thread(process_request_sync) → nuevo thread
    │
    ├── En thread separado:
    │   │
    │   ▼ _execute_pipeline() → sync
    │   │
    │   ▼ asyncio.run(run_nlu_and_ner_parallel())  ← NUEVO EVENT LOOP
    │   │         │
    │   │         ├─ NLU._arun() (async)
    │   │         └─ NER._arun() (async)
    │   │
    │   ▼ run_tool() → sync calls tool._run()
    │   │   │
    │   │   └─ LocationNERTool._run() → asyncio.run()  ← OTRO EVENT LOOP
    │   │
    │   ▼ LLM.invoke() → sync (langchain)
```

### 6.2 Problemas Identificados

#### CONC-01: `asyncio.run()` anidado (ALTO)

```python
# agent.py:230
nlu_raw, location_ner_raw = asyncio.run(run_nlu_and_ner_parallel())
```

`asyncio.run()` crea un **nuevo event loop**. Esto funciona porque `to_thread()` ejecuta en un hilo sin event loop propio. Pero:

1. **No se puede usar `await`** dentro de `_execute_pipeline()` — fuerza todo a ser sync con wrappers
2. **Incompatible con streaming** — para Server-Sent Events o WebSocket necesitas un pipeline async nativo
3. **Cada `asyncio.run()` tiene overhead** de crear/destruir event loop (~1-5ms)
4. **Si se elimina `to_thread()`** (optimización natural), el `asyncio.run()` falla con "cannot run nested event loop"

El mismo antipatrón aparece en `location_ner_tool.py:71`:
```python
result = asyncio.run(ner_service.extract_locations(...))
```

#### CONC-02: LLM invocación síncrona (MEDIO)

```python
# orchestrator.py:59
response = self.llm.invoke(prompt)  # Bloquea el thread ~1-3s
```

LangChain soporta `.ainvoke()` pero se usa `.invoke()` sync porque todo el pipeline es sync. Con tools reales (200-500ms cada una), el thread estará bloqueado 4-8 segundos por request.

#### CONC-03: Sin concurrency limits (MEDIO)

No hay límite de requests concurrentes al pipeline. Con el modelo actual (`to_thread`), cada request crea un thread + event loop. 100 requests simultáneos = 100 threads + 100 event loops + 100 llamadas paralelas a OpenAI.

### 6.3 Solución Recomendada

Convertir `_execute_pipeline` a **async nativo**:

```python
# Objetivo: pipeline completamente async
async def _execute_pipeline(self, user_input, profile_context=None):
    nlu_raw, ner_raw = await asyncio.gather(
        self.nlu._arun(user_input),
        self.location_ner._arun(user_input)
    )
    # ... entity resolution (sync, CPU-bound, OK) ...
    accessibility_raw = await self.accessibility._arun(nlu_raw)
    routes_raw, info_raw = await asyncio.gather(
        self.route._arun(accessibility_raw),
        self.tourism_info._arun(nlu_raw)
    )
    # ... build metadata (sync, OK) ...
```

Y en el orchestrator base:
```python
async def process_request(self, user_input, profile_context=None):
    tool_results, metadata = await self._execute_pipeline(user_input, profile_context)
    response = await self.llm.ainvoke(prompt)  # async LLM
    ...
```

Esto elimina `asyncio.run()`, `to_thread()`, y permite streaming futuro.

---

## 7. Contrato API y Flujo Frontend-Backend

### 7.1 Endpoints

| Método | Path | Request Model | Response Model | Consistente? |
|---|---|---|---|---|
| POST | `/chat/message` | `ChatMessageRequest` | `ChatResponse` | ✅ |
| GET | `/chat/conversation/{id}` | path param | `ConversationResponse` | ✅ |
| GET | `/chat/conversations` | query params | `ConversationListResponse` | ✅ |
| DELETE | `/chat/conversation/{id}` | path param | `dict` (raw) | ❌ |
| POST | `/chat/conversation/{id}/clear` | path param | `dict` (raw) | ❌ |
| POST | `/audio/transcribe` | `UploadFile` | `dict` (raw) | ❌ |
| POST | `/audio/validate` | `UploadFile` | `dict` (raw) | ❌ |
| GET | `/health/` | none | `SystemStatusResponse` | ✅ |
| GET | `/chat/demo/scenarios` | none | `dict` (raw) | ❌ |
| GET | `/chat/demo/responses` | none | `dict` (raw) | ❌ |

**5 de 14 endpoints** devuelven dicts crudos sin modelo Pydantic — el contrato no está formalizado para la mitad de la API.

### 7.2 ChatResponse — Contrato Principal

```python
class ChatResponse(BaseResponse):
    ai_response: Optional[str]           # Texto del LLM
    session_id: str                       # UUID de sesión
    processing_time: Optional[float]      # Segundos
    tourism_data: Optional[TourismData]   # Datos estructurados (venue, routes, accessibility)
    intent: Optional[str]                 # Del NLU
    entities: Optional[Dict]              # Del EntityResolver
    pipeline_steps: Optional[List[PipelineStep]]  # Timing por tool
    metadata: Optional[Dict]             # Raw (tool_outputs, tool_results_parsed)
```

**Problema:** `tourism_data` viene del backend como `dict` sin validación — se construye en `chat.py` via `backend_response.get("tourism_data")` sin pasar por `TourismData.model_validate()`. La validación ocurre en el canonicalizer, pero si falla, `tourism_data = None` silenciosamente.

### 7.3 Flujo de Datos Frontend

```
chat.js:sendToBackend()
    │
    ├─ Request: {message, conversation_id, user_preferences: {active_profile_id}}
    │
    ▼ Response consumed:
    │
    ├─ response.ai_response        → Chat bubble text
    ├─ response.tourism_data       → CardRenderer (venue card, route card, accessibility card)
    ├─ response.pipeline_steps     → PipelineVisualizer (step bars with timing)
    ├─ response.processing_time    → "Procesado en X.Xs"
    │
    ├─ response.intent             → NOT consumed by frontend
    ├─ response.entities           → NOT consumed by frontend
    └─ response.metadata           → NOT consumed by frontend
```

**Observación:** El frontend solo consume 4 de 8 campos del response. `intent`, `entities` y `metadata` se transmiten pero no se muestran — son útiles para debugging pero innecesarios en producción (bandwidth waste).

### 7.4 Inconsistencia `success` vs `status`

- Audio endpoints usan `"success": True/False`
- Chat endpoints usan `"status": "success"/"error"`
- Demo endpoints usan `"success": True` sin `status`

Esta inconsistencia complica el manejo de errores en el frontend.

---

## 8. Gestión de Sesiones y Estado

### 8.1 Estado Actual

```python
# conversation_service.py
class ConversationService:
    def __init__(self):
        self.conversations: Dict[str, List[Dict]] = {}      # In-memory
        self.session_metadata: Dict[str, Dict] = {}          # In-memory
```

**Características:**
- Almacenamiento volátil (se pierde al reiniciar)
- Sin TTL ni expiración de sesiones
- Sin vinculación a usuario (cualquiera puede acceder a cualquier session_id)
- Sin límite de mensajes por sesión
- Sin concurrent access protection (race conditions posibles)

### 8.2 Conversation History en el Orchestrator

```python
# orchestrator.py:86
self.conversation_history.append({"user": user_input, "assistant": text})
```

**Problema dual:** Hay DOS almacenamientos de historial:
1. `ConversationService.conversations` — usado por API
2. `orchestrator.conversation_history` — usado por el LLM (pero actualmente **no se pasa al LLM**)

El historial del orchestrator crece sin límite pero nunca se consume. Es un memory leak silencioso.

### 8.3 Recomendaciones

| Prioridad | Mejora |
|---|---|
| P0 | Eliminar `orchestrator.conversation_history` (no se usa) o implementar sliding window |
| P1 | Añadir TTL de 24h a sesiones en `ConversationService` |
| P1 | Migrar a SQLite mínimo para persistencia |
| P2 | Vincular session a user_id (cuando auth exista) |

---

## 9. Cobertura de Tests

### 9.1 Distribución

| Categoría | Tests | Archivos |
|---|---|---|
| Unit | 21 | test_nlu_models, test_nlu_interface, test_ner_interface, test_entity_resolver, test_tourism_nlu_tool, test_location_ner_tool |
| Integration | 27 | test_nlu_factory, test_keyword_nlu, test_openai_nlu, test_spacy_ner, test_ner_factory, test_tourism_agent_* |
| E2E / Application | 2 | test_chat_nlu_integration, test_chat_ner_integration |
| Evaluation | 2 | test_nlu_evaluation (corpus 80 muestras: keyword 70%, OpenAI 90%) |
| **Total** | **~73** | **17 archivos** |

### 9.2 Cobertura por Componente

| Componente | Cobertura | Calidad |
|---|---|---|
| NLU models (Pydantic) | Alta | 5 tests con validation, round-trip, defaults |
| NLU interface contract | Media | 3 tests verifican ABC compliance |
| NER interface contract | Media | 2 tests |
| Entity Resolver | **Alta** | 7 tests cubriendo 6 reglas de merge + conflictos |
| NLU Tool | Media | 3 tests (happy path + 2 fallback scenarios) |
| NER Tool | **Alta** | 8 tests (happy, error, empty, unavailable, async) |
| NLU Factory | **Alta** | 7 tests (creation, fallback, registration, unknown) |
| NER Factory | Media | 3 tests |
| OpenAI NLU service | Media | 4 tests (mocked) |
| Keyword NLU service | Media | 4 tests |
| spaCy NER service | Media | 4 tests (model mocked) |
| **Profile system** | **Parcial** | 7 tests de flow, **0** tests de propagación a tools |
| **Agent orchestrator** | **Baja** | Solo indirecto via tool tests. `_build_response_prompt`, `_extract_structured_data` sin tests |
| **Backend adapter** | **Ninguna** | 0 tests directos para 450+ líneas |
| **API endpoints** | **Mínima** | 2 tests superficiales |
| **Domain tools** | **Ninguna** | 0 tests para Accessibility, Routes, TourismInfo |
| **Canonicalizer** | **Ninguna** | 0 tests para normalización ES→EN |

### 9.3 Gaps Críticos

1. **Sin tests de timeout/latencia** — No se simula slow API, no se verifica degradación temporal
2. **Sin tests de concurrencia** — Thread safety no verificada
3. **Sin tests del LLM path** — `_build_response_prompt()` y `_extract_structured_data()` no testeados
4. **Sin contract tests tool output** — JSON schemas de tools no validados formalmente
5. **Sin tests de performance** — No hay benchmarks de latencia
6. **Backend adapter sin tests** — 450+ líneas de lógica de adaptación sin cobertura

### 9.4 Evaluación de Tests Existentes

**Fortalezas:**
- Corpus de evaluación NLU (80 muestras etiquetadas) — excelente para regression testing
- Error handling bien cubierto en NLU/NER (service unavailable, error status, empty input)
- Entity resolver exhaustivamente testeado

**Debilidades:**
- Tests demasiado enfocados en NLU/NER, poco en el resto del sistema
- Sin property-based testing (hypothesis)
- Sin load testing

---

## 10. Seguridad

### 10.1 Scorecard

| Categoría | Estado | Puntuación |
|---|---|---|
| Autenticación | No implementada | 0/10 |
| Autorización | No implementada | 0/10 |
| Validación de input | Pydantic en requests (message ≤1000 chars, audio ≤10MB) | 7/10 |
| Rate limiting | No implementado | 0/10 |
| CORS | Wildcard `*` en desarrollo y producción | 2/10 |
| HTTPS | No configurado (nginx solo HTTP) | 0/10 |
| Secrets management | git-crypt + GitHub Secrets, pero entrypoint logea nombres de keys | 5/10 |
| Data encryption | Ninguna (in-memory sin cifrado) | 0/10 |
| Dependency scanning | No existe en CI | 0/10 |
| **TOTAL** | | **1.5/10** |

### 10.2 Hallazgos Específicos

| ID | Severidad | Hallazgo |
|---|---|---|
| SEC-01 | **Crítica** | Sin autenticación — cualquier persona puede usar el sistema y acceder a cualquier conversación |
| SEC-02 | **Crítica** | Sin HTTPS — API keys y datos de usuario transmitidos en texto plano |
| SEC-03 | **Crítica** | Sin rate limiting — vulnerable a DoS y abuso de APIs (OpenAI, Google) con coste económico directo |
| SEC-04 | Alta | CORS `allow_origins=["*"]` en producción — permite requests desde cualquier dominio |
| SEC-05 | Alta | Container Docker ejecuta como root (UID 0) — compromiso de container = compromiso de host |
| SEC-06 | Media | `entrypoint.sh` logea nombres de environment variables de API keys — riesgo de exposición en CI logs |
| SEC-07 | Media | `conversation_id` generado con `Math.random()` — predecible, permite session hijacking si auth se implementa |
| SEC-08 | Media | Sin JSON payload size limit en API — OOM potencial con payloads grandes |
| SEC-09 | Baja | Nginx sin headers de seguridad: HSTS, CSP, Permissions-Policy, Referrer-Policy |

### 10.3 Mínimo para Producción

1. **JWT auth middleware** con extractor de user_id
2. **HTTPS termination** en nginx (Let's Encrypt)
3. **Rate limiting**: 10 req/min general, 5 req/min para `/chat/message`
4. **CORS allowlist** (no wildcard)
5. **Non-root Docker user**
6. **`pip-audit`** en CI

---

## 11. Infraestructura Docker y CI/CD

### 11.1 Docker

#### Dockerfile

**Fortalezas:**
- Multi-stage build (builder → runtime)
- `python:3.11-slim` como base
- CPU-only torch (ahorra ~1.5GB)
- Healthcheck declarativo

**Problemas:**

| ID | Severidad | Hallazgo |
|---|---|---|
| D-01 | **Crítica** | Sin `USER` directive — container ejecuta como root |
| D-02 | Alta | Imagen estimada ~1.2-1.5GB (torch 300MB + spaCy 400MB + audio libs 200MB) |
| D-03 | Media | Paquetes innecesarios: `libnss3`, `libcurl4`, `libpulse-mainloop-glib0` |
| D-04 | Baja | spaCy model hardcodeado en build arg — multi-idioma requiere rebuild |

#### docker-compose.prod.yml

| ID | Severidad | Hallazgo |
|---|---|---|
| D-05 | **Crítica** | Sin resource limits (`deploy.resources.limits`) — un container puede consumir toda la RAM/CPU del host |
| D-06 | Alta | Sin logging driver config — logs pueden llenar disco |
| D-07 | Alta | Nginx sin HTTPS (sección comentada) |
| D-08 | Media | Sin network isolation (default bridge) |

### 11.2 CI/CD (GitHub Actions)

#### Pipeline Actual

```
ci.yml:
  ├─ lint-format (ruff + mypy)
  ├─ tests (pytest, excluye slow+e2e)
  ├─ docker-build-validate (build + healthcheck)
  ├─ secrets-check (validates GitHub Secrets exist)
  └─ ci-summary (gate para merge)
```

**Fortalezas:**
- Pipeline multi-job con dependencias claras
- Coverage enforcement 70%
- Docker build validation con healthcheck real

**Problemas:**

| ID | Severidad | Hallazgo |
|---|---|---|
| CI-01 | **Crítica** | Sin security scanning (Trivy, bandit, pip-audit) |
| CI-02 | Alta | Tests excluyen `slow` y `e2e` — OpenAI NLU accuracy nunca se valida en CI |
| CI-03 | Alta | Sin deployment stage — solo build, nunca deploy |
| CI-04 | Media | Dummy API keys (`OPENAI_API_KEY=dummy_key`) — si `.env` se comete accidentalmente, las keys reales se usarían |
| CI-05 | Media | Sin image size check — imagen puede crecer sin detectarlo |
| CI-06 | Baja | Sin cache de dependencias Poetry — rebuild completo cada vez |

---

## 12. Observabilidad y Operaciones

### 12.1 Estado Actual

| Aspecto | Implementado | Detalle |
|---|---|---|
| Structured logging | ✅ Parcial | structlog usado, pero sin correlation_id por request |
| Pipeline timing | ✅ | `pipeline_steps` con `duration_ms` por tool |
| NER observability | ✅ | Log dedicado `location_ner_observability` con provider, model, latency |
| NLU observability | ✅ Parcial | Latencia en metadata, sin log dedicado para shadow mode comparison |
| Métricas | ❌ | Sin Prometheus, sin contadores, sin histogramas |
| Alertas | ❌ | Sin alerting de ningún tipo |
| Tracing distribuido | ❌ | Sin OpenTelemetry, sin trace propagation |
| Health check profundo | ❌ | Solo HTTP ping, no valida conectividad con OpenAI/Azure/spaCy |
| Cost tracking | ❌ | Sin tracking de tokens consumidos ni coste por API |

### 12.2 Mínimo para Producción

1. **Correlation ID** por request (header `X-Request-ID` propagado a todos los logs)
2. **Cost counter** acumulado por sesión (tokens OpenAI, calls Google APIs)
3. **Health check profundo** que valide:
   - OpenAI API key válida (1 token de test)
   - spaCy modelo cargado
   - Azure STT conectividad
4. **Métricas básicas**:
   - `voiceflow_request_duration_seconds` (histograma)
   - `voiceflow_tool_duration_seconds{tool=...}` (histograma)
   - `voiceflow_nlu_fallback_total` (counter)
   - `voiceflow_api_cost_cents` (gauge)

---

## 13. Evaluación Consolidada

### 13.1 Matriz de Madurez

```
                    POC    MVP    BETA   PROD
                    ───    ───    ────   ────
Arquitectura        ████████████░░░░░░░░░░░░  (75%)
NLU/NER             ██████████████████░░░░░░  (80%)
Domain Tools        ████░░░░░░░░░░░░░░░░░░░░  (20%)
Orquestación        ████████░░░░░░░░░░░░░░░░  (40%)
API Contract        ████████████░░░░░░░░░░░░  (60%)
Seguridad           ████░░░░░░░░░░░░░░░░░░░░  (15%)
Testing             ████████████░░░░░░░░░░░░  (60%)
Infraestructura     ██████████░░░░░░░░░░░░░░  (50%)
Observabilidad      ██████░░░░░░░░░░░░░░░░░░  (30%)
Perfiles            ████████░░░░░░░░░░░░░░░░  (40%)
```

### 13.2 Deuda Técnica Priorizada

| Prioridad | Item | Esfuerzo | Impacto |
|---|---|---|---|
| **P0** | Contratos tipados inter-tool | 2-3 días | Desbloquea integración APIs reales |
| **P0** | Pipeline async nativo (eliminar asyncio.run) | 1-2 días | Desbloquea streaming y WebSockets |
| **P0** | Auth + HTTPS + rate limiting | 3-4 días | Desbloquea cualquier despliegue |
| **P1** | Tools reales (Google Places + Directions) | 5-7 días | Entrega valor real al usuario |
| **P1** | Capa de resiliencia (circuit breaker, retry, budget) | 2-3 días | Estabilidad con APIs externas |
| **P1** | Tests del orchestrator y backend adapter | 2-3 días | Confianza en cambios |
| **P2** | Router por intent | 2-3 días | Reduce latencia y coste |
| **P2** | Profile → Tools → Ranking | 2-3 días | Perfiles funcionales |
| **P2** | Observabilidad (correlation ID, métricas, cost tracking) | 2-3 días | Operabilidad |
| **P3** | Docker hardening (non-root, limits, image optimization) | 1-2 días | Seguridad infraestructura |
| **P3** | CI/CD (security scanning, e2e tests, deployment pipeline) | 2-3 días | Deployment automatizado |
| **P3** | Session persistence (SQLite/PostgreSQL) | 2-3 días | Datos no se pierden |

---

## 14. Plan de Implementación — Ruta a Producción

### Fase 0: Contratos y Plumbing (Semana 1)

**Objetivo:** Establecer la infraestructura técnica que permita integrar APIs reales sin parches.

#### 0.1 Modelos inter-tool (`shared/models/tool_models.py`)

```python
class PlaceCandidate(BaseModel):
    """Resultado de búsqueda de lugar."""
    place_id: str                           # ID externo (Google Places)
    name: str
    address: Optional[str] = None
    location: Optional[tuple[float, float]] = None  # lat, lng
    types: list[str] = []                   # ["museum", "tourist_attraction"]
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    accessibility: Optional[AccessibilityInfo] = None
    source: str = "google_places"           # Trazabilidad de origen

class AccessibilityInfo(BaseModel):
    wheelchair_accessible_entrance: Optional[bool] = None
    level: Optional[str] = None             # Canonicalizado
    score: Optional[float] = None
    facilities: list[str] = []
    source: str = "unknown"                 # "google_places" | "local_db" | "user_report"

class RouteOption(BaseModel):
    origin: str
    destination: str
    mode: str                               # "transit" | "walking" | "driving"
    duration_text: str
    duration_seconds: int
    steps: list[str] = []
    accessibility_level: Optional[str] = None
    cost: Optional[str] = None
    source: str = "google_directions"

class VenueDetail(BaseModel):
    place_id: str
    name: str
    formatted_address: Optional[str] = None
    opening_hours: Optional[dict] = None
    pricing: Optional[dict] = None
    reviews_summary: Optional[str] = None
    accessibility: Optional[AccessibilityInfo] = None
    photos: list[str] = []                  # URLs
    source: str = "google_places"

class ToolPipelineContext(BaseModel):
    """Estado compartido del pipeline — pasa entre tools."""
    user_input: str
    nlu_result: Optional[NLUResult] = None
    resolved_entities: Optional[ResolvedEntities] = None
    ner_locations: list[str] = []
    profile_context: Optional[dict] = None
    candidates: list[PlaceCandidate] = []
    ranked_candidates: list[PlaceCandidate] = []
    venue_details: list[VenueDetail] = []
    routes: list[RouteOption] = []
    errors: list[str] = []                  # Errores parciales registrados
```

#### 0.2 Refactorizar tool signatures

**Antes:**
```python
class AccessibilityAnalysisTool(BaseTool):
    def _run(self, nlu_result: str) -> str:  # String in, string out
```

**Después:**
```python
class AccessibilityEnrichmentTool(BaseTool):
    async def _arun(self, context: ToolPipelineContext) -> ToolPipelineContext:
        # Enriquece context.candidates con datos de accesibilidad
        # Retorna context actualizado
```

#### 0.3 Pipeline async nativo

Convertir `_execute_pipeline` a async, eliminar `asyncio.run()` y `to_thread()`:

```python
async def _execute_pipeline(self, user_input, profile_context=None):
    context = ToolPipelineContext(user_input=user_input, profile_context=profile_context)

    # Paso 1: NLU + NER en paralelo
    nlu_raw, ner_raw = await asyncio.gather(
        self.nlu._arun(user_input),
        self.location_ner._arun(user_input)
    )
    context.nlu_result = parse_nlu(nlu_raw)
    context.ner_locations = parse_ner(ner_raw)
    context.resolved_entities = self.entity_resolver.resolve(...)

    # Paso 2: Tools de dominio (pueden paralelizarse)
    context = await self.places_search._arun(context)
    context = await self.accessibility_enrichment._arun(context)

    # Paso 3: Routes + ranking (paralelizables)
    context, _ = await asyncio.gather(
        self.directions._arun(context),
        self.ranking._arun(context)        # Aplica profile_context
    )

    return context
```

#### 0.4 Mover LLM model a Settings

```python
# settings.py — nuevo
llm_model: str = Field(default="gpt-4o-mini", description="LLM model for synthesis")
llm_temperature: float = Field(default=0.3)
llm_max_tokens: int = Field(default=2500)
```

**Entregables Fase 0:**
- [ ] `shared/models/tool_models.py` con 6 modelos Pydantic
- [ ] `_execute_pipeline` convertido a async
- [ ] Eliminación de todos los `asyncio.run()` anidados
- [ ] LLM model/temperature/max_tokens en Settings
- [ ] Tests unitarios para nuevos modelos

---

### Fase 1: Tools Reales (Semana 2-3)

**Objetivo:** Reemplazar stubs por integraciones con Google APIs, manteniendo fallback.

#### 1.1 PlacesSearchTool (reemplaza TourismInfoTool)

```python
class PlacesSearchTool(BaseTool):
    """Busca lugares relevantes usando Google Places API."""

    async def _arun(self, context: ToolPipelineContext) -> ToolPipelineContext:
        query = self._build_query(context)  # Usa NLU intent + entities + profile
        try:
            results = await self.google_client.text_search(
                query=query,
                location=context.resolved_entities.destination,
                type_filter=self._get_type_filter(context.profile_context)
            )
            context.candidates = [self._to_candidate(r) for r in results[:10]]
        except GoogleAPIError as e:
            context.errors.append(f"PlacesSearch: {e}")
            context.candidates = self._local_fallback(context)  # VENUE_DB actual
        return context
```

**Provider:** Google Places API (Text Search + Place Details)
**Fallback:** `VENUE_DB` actual como cache local
**Coste:** ~$0.032 per Text Search + $0.017 per Place Details

#### 1.2 DirectionsTool (reemplaza RoutePlanningTool)

```python
class DirectionsTool(BaseTool):
    """Calcula rutas accesibles usando Google Directions API."""

    async def _arun(self, context: ToolPipelineContext) -> ToolPipelineContext:
        for candidate in context.ranked_candidates[:3]:  # Top 3 solo
            try:
                routes = await self.google_client.directions(
                    origin=context.user_location or "Madrid centro",
                    destination=candidate.address,
                    mode="transit",
                    alternatives=True
                )
                context.routes.extend([self._to_route(r) for r in routes])
            except GoogleAPIError as e:
                context.errors.append(f"Directions to {candidate.name}: {e}")
        return context
```

**Provider:** Google Directions API
**Coste:** ~$0.005-0.01 per request

#### 1.3 AccessibilityEnrichmentTool (reemplaza AccessibilityAnalysisTool)

```python
class AccessibilityEnrichmentTool(BaseTool):
    """Enriquece candidatos con datos de accesibilidad."""

    async def _arun(self, context: ToolPipelineContext) -> ToolPipelineContext:
        for candidate in context.candidates:
            try:
                details = await self.google_client.place_details(
                    place_id=candidate.place_id,
                    fields=["wheelchair_accessible_entrance", "reviews"]
                )
                candidate.accessibility = self._extract_accessibility(details)
            except GoogleAPIError as e:
                # Fallback a datos locales si existen
                candidate.accessibility = self._local_fallback(candidate.name)
                context.errors.append(f"Accessibility {candidate.name}: {e}")
        return context
```

#### 1.4 Capa de resiliencia (`integration/external_apis/resilience.py`)

```python
class ResilientAPIClient:
    """Wrapper con circuit breaker, retry y rate limiting."""

    def __init__(self, name: str, settings: Settings):
        self.rate_limiter = TokenBucketRateLimiter(
            tokens_per_second=settings.google_api_rps or 10
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            name=name
        )
        self.budget_tracker = BudgetTracker(
            max_cost_per_hour=settings.api_budget_per_hour or 1.0
        )

    async def call(self, fn, *args, **kwargs):
        if self.budget_tracker.is_over_budget():
            raise BudgetExhaustedError(f"{self.name} budget exceeded")

        await self.rate_limiter.acquire()

        if not self.circuit_breaker.allow_request():
            raise CircuitOpenError(f"{self.name} circuit open")

        try:
            result = await fn(*args, **kwargs)
            self.circuit_breaker.record_success()
            self.budget_tracker.record_cost(self._estimate_cost(fn))
            return result
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
```

**Entregables Fase 1:**
- [ ] `integration/external_apis/google_places_client.py`
- [ ] `integration/external_apis/google_directions_client.py`
- [ ] `integration/external_apis/resilience.py` (rate limiter + circuit breaker + budget)
- [ ] `business/domains/tourism/tools/places_search_tool.py`
- [ ] `business/domains/tourism/tools/directions_tool.py`
- [ ] `business/domains/tourism/tools/accessibility_enrichment_tool.py`
- [ ] Settings para Google APIs (`VOICEFLOW_GOOGLE_API_KEY`, `VOICEFLOW_API_BUDGET_PER_HOUR`)
- [ ] Tests con mocks de Google APIs
- [ ] Tests de resiliencia (timeout, circuit breaker, budget)
- [ ] Mantener tools antiguas como fallback local

---

### Fase 2: Routing + Profiles + API Hardening (Semana 3-4)

**Objetivo:** Ejecutar solo tools necesarias, perfiles funcionales, API production-ready.

#### 2.1 Intent Router

```python
INTENT_TOOL_MAP = {
    "route_planning":       ["places_search", "accessibility", "directions"],
    "event_search":         ["places_search", "accessibility"],
    "restaurant_search":    ["places_search", "accessibility"],
    "accommodation_search": ["places_search", "accessibility"],
    "general_query":        [],  # Solo LLM, sin tools de dominio
}
```

#### 2.2 ProfileRankingStep

```python
class ProfileRankingStep:
    """Reordena candidatos según profile_context.ranking_bias."""

    async def run(self, context: ToolPipelineContext) -> ToolPipelineContext:
        if not context.profile_context or not context.candidates:
            context.ranked_candidates = context.candidates
            return context

        bias = context.profile_context.get("ranking_bias", {})
        venue_weights = bias.get("venue_types", {})

        scored = []
        for candidate in context.candidates:
            base_score = candidate.rating or 3.0
            profile_boost = max(
                venue_weights.get(t, 1.0) for t in candidate.types
            ) if candidate.types else 1.0
            scored.append((candidate, base_score * profile_boost))

        scored.sort(key=lambda x: x[1], reverse=True)
        context.ranked_candidates = [c for c, _ in scored]
        return context
```

#### 2.3 Auth + HTTPS + Rate Limiting

```python
# middleware/auth.py
class JWTAuthMiddleware:
    async def __call__(self, request, call_next):
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)  # Health sin auth
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return JSONResponse(401, {"detail": "Missing token"})
        user = verify_jwt(token)
        request.state.user_id = user.id
        return await call_next(request)
```

```nginx
# nginx.conf — rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=chat:10m rate=3r/s;

location /api/v1/chat/message {
    limit_req zone=chat burst=5 nodelay;
    proxy_pass http://app;
}
```

**Entregables Fase 2:**
- [ ] Intent router en `agent.py`
- [ ] `ProfileRankingStep` con tests
- [ ] Profile propagation a PlacesSearchTool (type_filter por perfil)
- [ ] JWT auth middleware
- [ ] HTTPS en nginx (Let's Encrypt)
- [ ] Rate limiting en nginx
- [ ] CORS allowlist (no wildcard)
- [ ] Non-root Docker user
- [ ] API response standardization (Pydantic models para todos los endpoints)
- [ ] Tests de integración del router + ranking

---

### Fase 3: Observabilidad y Operaciones (Semana 4-5)

**Objetivo:** Instrumentar para operar con confianza.

#### 3.1 Observabilidad

- [ ] Correlation ID middleware (genera `X-Request-ID`, propaga a structlog)
- [ ] Cost tracking per request (tokens OpenAI + Google API calls)
- [ ] Métricas Prometheus:
  - `voiceflow_request_duration_seconds{endpoint}`
  - `voiceflow_tool_duration_seconds{tool, status}`
  - `voiceflow_nlu_provider_used{provider}`
  - `voiceflow_api_cost_cents{provider}`
  - `voiceflow_circuit_breaker_state{service}`
- [ ] Health check profundo (valida OpenAI key, spaCy model, Google API key)

#### 3.2 CI/CD

- [ ] Security scanning (Trivy + bandit + pip-audit)
- [ ] Image size check (fail if >1.5GB)
- [ ] E2e test nightly (con API keys reales, marcador `@slow`)
- [ ] Staging deployment job
- [ ] Cache de dependencias Poetry

#### 3.3 Persistencia

- [ ] SQLite para ConversationService (mínimo viable)
- [ ] TTL de 24h en sesiones
- [ ] Eliminar `orchestrator.conversation_history` (o implementar sliding window de N turnos)

#### 3.4 Docker Hardening

```dockerfile
# Añadir al Dockerfile
RUN useradd -m -u 1000 -s /bin/bash voiceflow
USER voiceflow

# docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      memory: 1G
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "5"
```

**Entregables Fase 3:**
- [ ] Middleware correlation ID
- [ ] Cost tracking en resilience layer
- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] Health check profundo en `/api/v1/health/`
- [ ] CI: Trivy + bandit + pip-audit + image size check
- [ ] Staging deployment pipeline
- [ ] SQLite conversation storage
- [ ] Session TTL
- [ ] Docker hardening (non-root, limits, logging)

---

## 15. Riesgos y Mitigaciones

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | Google Places rate limit en free tier (17K requests/mes) | Alta | Alto | Cache agresivo (TTL 24h por place_id), batch place_details, degradación a datos locales |
| R2 | Latencia total >5s con APIs reales | Alta | Alto | Paralelizar PlacesSearch + Directions; cache; timeout 3s con fallback LLM |
| R3 | Coste OpenAI (gpt-4 para síntesis = ~$0.03/request) | Alta | Medio | Migrar síntesis a gpt-4o-mini ($0.0015/request) — 20x ahorro. Evaluar calidad con A/B test |
| R4 | Google API key comprometida | Media | Crítico | Restricción por IP/referer en Google Console, budget caps, rotation via secrets manager |
| R5 | spaCy NER no reconoce venues específicos | Media | Bajo | EntityResolver ya compensa con NLU; Google Places Text Search es fuzzy |
| R6 | LLM genera JSON inválido en `_extract_structured_data` | Alta | Bajo | Con tools reales, eliminar lógica de "prefer LLM over tools". Tools = ground truth |
| R7 | Migración async rompe tests existentes | Media | Medio | Feature flag `VOICEFLOW_ASYNC_PIPELINE=true/false`, migración gradual |
| R8 | Frontend no adapta a nuevo response format | Baja | Medio | `tourism_data` schema ya definido en Pydantic — frontend ya lo consume. Cambios internos al pipeline son transparentes |

---

## Apéndice A: Archivos Clave por Fase

### Fase 0 (crear/modificar)
```
shared/models/tool_models.py               ← CREAR
business/core/orchestrator.py              ← MODIFICAR (async)
business/domains/tourism/agent.py          ← MODIFICAR (async pipeline)
business/domains/tourism/tools/*.py        ← MODIFICAR (signatures)
integration/configuration/settings.py      ← MODIFICAR (LLM settings)
tests/test_shared/test_tool_models.py      ← CREAR
```

### Fase 1 (crear/modificar)
```
integration/external_apis/google_places_client.py     ← CREAR
integration/external_apis/google_directions_client.py  ← CREAR
integration/external_apis/resilience.py                ← CREAR
business/domains/tourism/tools/places_search_tool.py   ← CREAR
business/domains/tourism/tools/directions_tool.py      ← CREAR
business/domains/tourism/tools/accessibility_enrichment_tool.py ← CREAR
integration/configuration/settings.py                  ← MODIFICAR
tests/test_integration/test_google_*.py               ← CREAR
tests/test_business/test_resilience.py                 ← CREAR
```

### Fase 2 (crear/modificar)
```
business/domains/tourism/agent.py              ← MODIFICAR (router)
business/domains/tourism/ranking.py            ← CREAR
application/middleware/auth.py                 ← CREAR
application/middleware/rate_limit.py           ← CREAR
docker/nginx/nginx.conf                        ← MODIFICAR (HTTPS, rate limit)
Dockerfile                                     ← MODIFICAR (non-root)
tests/test_business/test_ranking.py            ← CREAR
tests/test_application/test_auth.py            ← CREAR
```

### Fase 3 (crear/modificar)
```
application/middleware/correlation_id.py       ← CREAR
application/api/v1/metrics.py                  ← CREAR
integration/data_persistence/sqlite_repo.py    ← CREAR
.github/workflows/ci.yml                      ← MODIFICAR
docker-compose.prod.yml                       ← MODIFICAR
```

---

## Apéndice B: Settings Nuevos Necesarios

```python
# Fase 0
llm_model: str = "gpt-4o-mini"
llm_temperature: float = 0.3
llm_max_tokens: int = 2500
async_pipeline: bool = True

# Fase 1
google_api_key: Optional[str] = None
google_api_rps: int = 10                    # Requests per second
api_budget_per_hour: float = 1.0            # USD
google_places_cache_ttl: int = 86400        # 24h en segundos
tool_timeout_seconds: float = 3.0
circuit_breaker_threshold: int = 5
circuit_breaker_recovery_seconds: int = 60

# Fase 2
auth_enabled: bool = False
auth_jwt_secret: Optional[str] = None
auth_jwt_algorithm: str = "HS256"
rate_limit_general: int = 10                # req/min
rate_limit_chat: int = 5                    # req/min

# Fase 3
metrics_enabled: bool = False
database_url: str = "sqlite:///voiceflow.db"
session_ttl_hours: int = 24
```

---

## 16. Análisis de APIs, Frameworks y Enfoque RAG para Tools Reales

> **Objetivo de esta sección:** Proporcionar toda la información técnica necesaria para decidir
> la estrategia de datos del sistema antes de implementar las tools reales (Fase 1).
> Se presentan dos enfoques: **API-first** y **RAG-first**, con una recomendación híbrida.

---

### 16.1 APIs de Búsqueda de Lugares (POI)

#### Google Places API (New)

| Aspecto | Detalle |
|---|---|
| **Pricing (post-Marzo 2025)** | Place Details Essentials: $5/1K req (10K free/mes). Place Details Pro: $17/1K req (5K free/mes). Text Search: $32/1K req (5K free/mes) |
| **Free tier efectivo** | ~10K Place Details + 5K Text Search = suficiente para POC/demo |
| **Campos de accesibilidad** | `accessibilityOptions.wheelchairAccessibleEntrance`, `.wheelchairAccessibleParking`, `.wheelchairAccessibleRestroom`, `.wheelchairAccessibleSeating` — disponibles en tier Essentials |
| **Cobertura España** | Excelente en zonas urbanas. Mejor fuente comercial de datos estructurados |
| **Multi-ciudad** | Global, funciona igual para Madrid, Barcelona, Sevilla, Granada |
| **Ventajas** | Datos de accesibilidad estructurados (4 campos wheelchair), reviews, fotos, horarios, precios. Único proveedor comercial con datos de accesibilidad explícitos |
| **Limitaciones** | Facturación por el SKU más alto de cualquier campo solicitado. A escala, coste significativo |

**Veredicto:** Mejor fuente individual para datos estructurados de accesibilidad en contexto comercial. El free tier es viable para demo técnica.

#### OpenTripMap API

| Aspecto | Detalle |
|---|---|
| **Pricing** | Gratuito: $0/mes, 10 req/s, 5.000 req/día, **uso no-comercial** |
| **Datos** | 10M+ atracciones turísticas. Fuentes: OpenStreetMap + Wikidata + Wikipedia |
| **Campos** | Nombre, dirección, descripción, URL, imagen, categorías, coordenadas |
| **Accesibilidad** | **Ningún dato estructurado de accesibilidad** |
| **Planes de pago** | Desde ~$19/mes (vía RapidAPI) para uso comercial |

**Veredicto:** Buen suplemento gratuito para descubrimiento de POI y descripciones textuales. Sin datos de accesibilidad. Útil como fuente de enriquecimiento para RAG (descripciones de Wikipedia).

#### Foursquare Places API

| Aspecto | Detalle |
|---|---|
| **Free tier** | $200/mes en créditos. 10K calls/mes a endpoints Pro (nombre, dirección, categoría) |
| **Premium** | Fotos, tips, horarios, ratings: $18.75/1K calls (sin free tier) |
| **Calidad** | 100M+ POIs globalmente — una de las bases de datos más completas |
| **Accesibilidad** | **Ningún dato estructurado de accesibilidad** |
| **España** | Buena cobertura urbana, especialmente restaurantes/bares |

**Veredicto:** Excelente calidad de POI pero sin datos de accesibilidad. Caro si necesitas campos premium.

#### Overpass API (OpenStreetMap)

| Aspecto | Detalle |
|---|---|
| **Pricing** | **Completamente gratuito**, sin API key |
| **Rate limits** | 2-4 requests concurrentes por IP. Sin cap diario. Self-hosteable |
| **Tags de accesibilidad disponibles** | `wheelchair=yes\|limited\|no`, `tactile_paving`, `kerb=lowered\|flush`, `ramp`, `elevator`, `toilets:wheelchair`, `surface`, `incline`, `width` |
| **Cobertura España** | Inconsistente — POIs turísticos principales en Madrid/Barcelona tienen tags, pero la mayoría de restaurantes, tiendas y venues menores NO |
| **Multi-ciudad** | Global, datos para cualquier ciudad del mundo |

**Query de ejemplo (restaurantes accesibles en Madrid):**
```
[out:json][timeout:30];
area["name"="Madrid"]["boundary"="administrative"]->.searchArea;
(
  node["amenity"="restaurant"]["wheelchair"="yes"](area.searchArea);
  way["amenity"="restaurant"]["wheelchair"="yes"](area.searchArea);
);
out body;
```

**Veredicto:** Fuente más rica de tags de accesibilidad cruda, completamente gratuita. Cobertura irregular en España — ideal como complemento de Google Places, no como fuente única. **Excelente candidato para ingesta en RAG.**

#### HERE Places API

| Aspecto | Detalle |
|---|---|
| **Free tier** | 250.000 transacciones/mes (muy generoso) |
| **Accesibilidad** | **Ningún dato de accesibilidad** |

**Veredicto:** Generoso pero sin datos de accesibilidad. Útil solo como fallback de geocoding.

#### Yelp Fusion API

| Aspecto | Detalle |
|---|---|
| **Pricing** | $7.99-$14.99/1K calls. 5K free en trial de 30 días |
| **España** | **Cobertura débil** — Yelp no es popular en España (dominan Google Maps y TripAdvisor) |
| **Accesibilidad** | Ningún dato |

**Veredicto:** No recomendado para este proyecto. Cobertura pobre en España.

### 16.2 APIs de Routing/Direcciones

#### Google Routes API

| Aspecto | Detalle |
|---|---|
| **Pricing** | Essentials: $5/1K (10K free/mes). Pro: $10/1K (5K free/mes) |
| **Transit** | Soporta modo `TRANSIT` con opción `wheelchair accessible` |
| **Diferenciador** | **Único API comercial con routing de transporte accesible** — evita escaleras, prefiere ascensores, rutas adaptadas |

**Veredicto:** Indispensable para rutas de transporte accesible. No hay alternativa comparable.

#### OpenRouteService (wheelchair profile)

| Aspecto | Detalle |
|---|---|
| **Pricing** | **Gratuito permanente** (Standard plan). Open source, self-hosteable |
| **Límites Standard** | 2.000 directions/día, 40/minuto |
| **Perfil wheelchair** | **Dedicado**, con parámetros: inclinación máxima (1-15%), tipo de superficie mínimo, smoothness, altura de bordillo, evitar escaleras |
| **Self-hosting** | Elimina todos los límites. Docker image disponible |

**Veredicto:** El mejor motor de routing específico para sillas de ruedas. Parámetros de superficie, inclinación y bordillo son exactamente lo que necesita un proyecto de accesibilidad. **Recomendado como complemento de Google Routes** — Google para transit, OpenRouteService para walking/wheelchair.

#### OSRM

| Aspecto | Detalle |
|---|---|
| **Pricing** | Gratuito, open source (C++, self-hosted) |
| **Wheelchair** | **Sin perfil wheelchair nativo** — requiere custom Lua profile |
| **Performance** | Extremadamente rápido |

**Veredicto:** Demasiado esfuerzo de customización. OpenRouteService ofrece wheelchair routing out-of-the-box.

#### Mapbox Directions

| Aspecto | Detalle |
|---|---|
| **Free tier** | 100.000 req/mes |
| **Transit** | **No soportado** (Mapbox eliminó transit) |
| **Wheelchair** | **Sin perfil** |

**Veredicto:** No apto para este proyecto (sin transit ni wheelchair).

### 16.3 Fuentes de Datos de Accesibilidad

#### TUR4all / PREDIF (España)

| Aspecto | Detalle |
|---|---|
| **Organización** | PREDIF — plataforma referente de turismo accesible en España |
| **Datos** | 4.000+ establecimientos turísticos evaluados. 1.300+ perfiles detallados de accesibilidad |
| **Categorías** | Hoteles, restaurantes, museos, monumentos, espacios naturales, playas, transporte |
| **Detalle por establecimiento** | Accesibilidad física, visual, auditiva. Lectura fácil. Info general |
| **API** | **No existe API pública**. Solo acceso via web y app móvil |
| **Idiomas** | 11 idiomas incluyendo español, inglés, francés, alemán |

**Veredicto:** La fuente de datos de accesibilidad turística más valiosa para España. Sin API pública — requiere contacto directo con PREDIF para partnership de datos, o ingesta manual para RAG.

#### Wheelmap.org

| Aspecto | Detalle |
|---|---|
| **Datos** | 3.2M places globalmente con info de accesibilidad (wheelchair) |
| **API** | REST API en `wheelmap.org/api` — requiere API key (gratuita) |
| **Estándar** | A11yJSON — 150+ criterios de accesibilidad |
| **España** | Cobertura basada en OSM wheelchair tags (irregular) |

**Veredicto:** Útil como overlay de datos wheelchair. API gratuita y estándar A11yJSON interesante como referencia de schema.

#### Datos gubernamentales (datos.gob.es + Dataestur)

| Aspecto | Detalle |
|---|---|
| **datos.gob.es** | ~3.000 datasets de turismo. Formatos: CSV, JSON, XML, RDF |
| **Dataestur (SEGITTUR)** | Agregador nacional de datos turísticos con API REST |
| **Contenido** | Atracciones por municipio, alojamientos registrados, playas, patrimonio cultural |
| **Accesibilidad** | Datos limitados — no es el foco principal |

**Veredicto:** Buena fuente complementaria para metadatos turísticos (ubicaciones, categorías, estadísticas). No reemplaza TUR4all para accesibilidad.

### 16.4 Matriz Comparativa — APIs

```
                        Coste       Accesibilidad   Cobertura ES   Multi-ciudad   Para RAG
                        ─────       ─────────────   ────────────   ────────────   ────────
Google Places           $$$         ████████ (4/4)   ██████████     ██████████     Parcial
OpenTripMap             Free*       ░░░░░░░░ (0/4)   ████████░░     ██████████     ████████
Foursquare              $$          ░░░░░░░░ (0/4)   ████████░░     ██████████     ██████░░
Overpass/OSM            Free        ██████░░ (tags)  ██████░░░░     ██████████     ██████████
TUR4all/PREDIF          Free**      ██████████ (10)  ██████████     ████░░░░░░     ██████████
Wheelmap                Free        ████░░░░ (1/4)   ████░░░░░░     ██████████     ████████░░
datos.gob.es            Free        ██░░░░░░ (meta)  ██████████     ██████████     ██████████

Google Routes           $$          ████████ (transit wheelchair)    ██████████     N/A
OpenRouteService        Free        ██████████ (perfil wheelchair)  ██████████     N/A
```

`*` Free para uso no-comercial | `**` Sin API, requiere ingesta manual

### 16.5 Stack Recomendado — Enfoque API-First

Para una **demo técnica sin presupuesto definido**, la combinación recomendada es:

| Capa | Proveedor | Justificación |
|---|---|---|
| **Búsqueda de lugares** | Google Places API (New) | Única fuente con 4 campos wheelchair estructurados. Free tier suficiente para demo |
| **Routing accesible (walking)** | OpenRouteService | Gratuito, perfil wheelchair dedicado con surface/incline/kerb |
| **Routing transporte público** | Google Routes API | Único con transit wheelchair routing |
| **Enriquecimiento accesibilidad** | Google Places (detalles) + Overpass API (tags OSM) | Doble fuente: Google para datos comerciales, OSM para tags comunitarios |
| **Fallback** | Datos locales actuales (`VENUE_DB`, `ROUTE_DB`, `ACCESSIBILITY_DB`) | Cuando APIs fallan o presupuesto se agota |

**Coste estimado para demo (~100 queries/día):**
- Google Places: ~3K Text Search + 3K Details/mes ≈ **$0** (dentro del free tier)
- Google Routes: ~3K/mes ≈ **$0** (dentro del free tier)
- OpenRouteService: ~3K/mes ≈ **$0** (dentro de 2K/día)
- **Total: $0/mes** para volumen de demo

---

### 16.6 Enfoque RAG — Arquitectura Completa

#### 16.6.1 Por qué RAG

El enfoque RAG (Retrieval-Augmented Generation) es la **alternativa a largo plazo** a las APIs en tiempo real:

| Aspecto | API-First | RAG-First |
|---|---|---|
| **Latencia** | 200-500ms por API call | 10-50ms por búsqueda vectorial |
| **Coste por query** | $0.01-0.05 (Google + OpenAI) | ~$0 (búsqueda local) + coste de embedding |
| **Frescura de datos** | Tiempo real | Tan fresco como el último sync (horas/días) |
| **Cobertura** | Limitada a lo que devuelve la API | Controlada por lo que se ingesta |
| **Offline** | Imposible | Posible (con embeddings locales) |
| **Escalabilidad** | Limitada por rate limits y presupuesto | Limitada por storage y RAM |
| **Control de datos** | Dependes del proveedor | Datos propios, curados, verificados |

**Recomendación:** Implementar RAG como **segunda fase** (después de validar el pipeline con APIs) o como **enfoque primario** si el presupuesto de APIs es restrictivo.

#### 16.6.2 Arquitectura RAG Propuesta

```
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE (offline)                 │
│                                                                  │
│  Fuentes de datos:                                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ OSM Spain    │ │ TUR4all      │ │ datos.gob.es │            │
│  │ (PBF dump)   │ │ (web scrape) │ │ (API/CSV)    │            │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘            │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────────────────────────────────────┐                │
│  │           ETL / Normalización                │                │
│  │  - Normalizar schemas a PlaceCandidate      │                │
│  │  - Merge datos de múltiples fuentes         │                │
│  │  - Generar texto descriptivo para embedding │                │
│  │  - Validar y canonicalizar accesibilidad    │                │
│  └──────────────────┬──────────────────────────┘                │
│                     │                                            │
│                     ▼                                            │
│  ┌─────────────────────────────────────────────┐                │
│  │         Embedding + Indexación               │                │
│  │  - Texto → embedding vectorial              │                │
│  │  - Store: metadatos + vector + raw text     │                │
│  │  - Índices: por ciudad, tipo, accesibilidad │                │
│  └──────────────────┬──────────────────────────┘                │
│                     │                                            │
│                     ▼                                            │
│  ┌─────────────────────────────────────────────┐                │
│  │         Vector Database                      │                │
│  │  PostgreSQL + pgvector                       │                │
│  │  (o LanceDB para embedded)                   │                │
│  └─────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     QUERY PIPELINE (runtime)                     │
│                                                                  │
│  User: "Restaurantes accesibles en Granada"                      │
│         │                                                        │
│         ▼                                                        │
│  NLU → intent=restaurant_search, entities={dest: Granada}        │
│         │                                                        │
│         ▼                                                        │
│  RAGSearchTool:                                                  │
│    1. Construir query: "restaurante accesible Granada"           │
│    2. Embed query → vector                                       │
│    3. Búsqueda vectorial + filtros metadata:                     │
│       WHERE city = 'Granada'                                     │
│       AND type IN ('restaurant', 'cafe')                         │
│       AND wheelchair IS NOT NULL                                 │
│       ORDER BY vector_similarity DESC                            │
│       LIMIT 10                                                   │
│    4. Retornar list[PlaceCandidate] con datos de accesibilidad   │
│         │                                                        │
│         ▼                                                        │
│  Ranking (profile_context) → Rutas (OpenRouteService) → LLM     │
└─────────────────────────────────────────────────────────────────┘
```

#### 16.6.3 Fuentes de Datos para Ingesta RAG

##### Fuente 1: OpenStreetMap Spain Extract

| Aspecto | Detalle |
|---|---|
| **Tamaño** | ~1.3 GB (formato PBF) |
| **Descarga** | [Geofabrik Spain](https://download.geofabrik.de/europe/spain.html) — actualización diaria |
| **Sub-regiones** | Disponibles (Madrid, Barcelona, etc.) para desarrollo |
| **Herramientas** | `osmium` (CLI), `pyrosm` (Python), `osmnx` (Python graphs) |
| **Datos relevantes** | Todos los `tourism=*`, `amenity=*`, `leisure=*` con tags `wheelchair`, `tactile_paving`, `surface`, `incline` |
| **Formato PBF** | 50% más pequeño que XML comprimido, 5x más rápido de leer |

**Pipeline de extracción:**
```python
# Ejemplo con pyrosm
from pyrosm import OSM

osm = OSM("spain-latest.osm.pbf", bounding_box=[madrid_bbox])

# Extraer POIs turísticos con tags de accesibilidad
pois = osm.get_pois(custom_filter={
    "tourism": True,
    "amenity": ["restaurant", "cafe", "museum", "theatre", "library"],
    "leisure": ["park", "garden", "stadium"]
})

# Filtrar los que tienen información de accesibilidad
accessible_pois = pois[pois["wheelchair"].notna()]
```

**Estimación para España completa:**
- POIs turísticos: ~500K-1M nodos
- Con tag `wheelchair`: ~5-15% (depende de la zona)
- Tamaño en DB tras extracción: ~200-500 MB

##### Fuente 2: TUR4all / PREDIF

| Aspecto | Detalle |
|---|---|
| **Acceso** | Web scraping de `tur4all.com` (no hay API) |
| **Contenido** | Fichas detalladas: accesibilidad física, visual, auditiva por establecimiento |
| **Volumen** | ~4.000 establecimientos |
| **Herramientas** | `scrapy` + `beautifulsoup4` o `playwright` (si requiere JS rendering) |
| **Consideraciones legales** | Datos públicos, pero se recomienda contactar PREDIF para partnership formal. Respetar `robots.txt` y rate-limit de scraping |

**Pipeline de ingesta:**
```python
# Esquema de datos TUR4all (estimado por estructura web)
class TUR4allVenue:
    name: str
    city: str
    category: str                    # hotel, restaurante, museo, etc.
    physical_accessibility: dict     # rampas, ascensores, baños
    visual_accessibility: dict       # braille, contraste, guías
    auditory_accessibility: dict     # bucle inductivo, intérprete LSE
    general_info: str                # descripción general
    address: str
    coordinates: Optional[tuple]
    photos: list[str]
```

**Valor:** Esta es la fuente de accesibilidad más detallada y verificada para España. Cada ficha tiene evaluación profesional de accesibilidad, no solo tags crowdsourced.

##### Fuente 3: datos.gob.es + Portales Regionales

| Aspecto | Detalle |
|---|---|
| **API** | REST API disponible. Paquete `opendataes` (R) para acceso programático |
| **Datasets relevantes** | Atracciones turísticas por municipio, alojamientos registrados, playas, patrimonio cultural, oficinas de turismo |
| **Formatos** | CSV, JSON, XML, RDF |
| **Portales regionales** | Madrid Destino, Turisme de Barcelona, Andalucia.org — cada uno con datos propios |

**Valor para RAG:** Metadatos oficiales (categorías, ubicaciones, descripciones institucionales). No contiene datos de accesibilidad detallados pero sí coordenadas y clasificaciones oficiales que complementan OSM y TUR4all.

##### Fuente 4: OpenTripMap (descripciones Wikipedia)

| Aspecto | Detalle |
|---|---|
| **API** | Gratuita, 5K req/día |
| **Valor para RAG** | Descripciones textuales de Wikipedia/Wikidata para cada POI — ideales para embedding semántico |
| **Pipeline** | Query radius por ciudad → extraer `xid` → fetch detail con `wikipedia_extracts` |

##### Fuente 5: Google Places (enriquecimiento puntual)

| Aspecto | Detalle |
|---|---|
| **Uso en RAG** | Enriquecer venues del RAG con datos frescos de Google (reviews, horarios actuales, fotos) |
| **Estrategia** | Batch nightly: para los top 1000 venues por ciudad, fetch Place Details y actualizar DB |
| **Coste** | ~1K Details/noche × $0.005 = ~$5/mes por ciudad |

#### 16.6.4 Vector Database — Comparativa

| Base de datos | Tipo | Licencia | Self-hosted | Español | Mejor para |
|---|---|---|---|---|---|
| **pgvector** | Extensión PostgreSQL | PostgreSQL license | Sí | N/A (embedding agnostic) | **Proyecto que ya usa/usará PostgreSQL. Una sola DB para todo** |
| **LanceDB** | Embedded (como SQLite) | Apache 2.0 | Sí (sin servidor) | N/A | **POC rápido, zero-config, sin infra extra** |
| **ChromaDB** | Embedded / client-server | Apache 2.0 | Sí | N/A | Prototipado rápido con LangChain |
| **Qdrant** | Servidor dedicado | Apache 2.0 | Sí (Docker) | N/A | Alto volumen, filtrado avanzado por payload |
| **Weaviate** | Servidor dedicado | BSD-3 | Sí | N/A | Búsqueda híbrida (semántica + keyword) |
| **FAISS** | Librería (no DB) | MIT | N/A | N/A | Componente interno, no usar directamente |

**Recomendación por escenario:**

| Escenario | Recomendación | Justificación |
|---|---|---|
| **Demo técnica (ahora)** | **LanceDB** | Zero-config, embedded, sin servidor, se ejecuta dentro del mismo proceso Python. Perfecto para POC |
| **Producción MVP** | **pgvector** | Si se migra a PostgreSQL (ya contemplado en roadmap como Fase 3), pgvector unifica datos relacionales + vectoriales en una sola DB. Simplifica operaciones |
| **Producción a escala** | **Qdrant** | Si el volumen de POIs supera 1M y se necesita filtrado avanzado (por ciudad, tipo, accesibilidad) integrado en la búsqueda vectorial |

#### 16.6.5 Modelos de Embedding — Comparativa

| Modelo | Dimensiones | Español | Coste | Dónde se ejecuta |
|---|---|---|---|---|
| **OpenAI text-embedding-3-small** | 1.536 | Excelente (90+ idiomas) | $0.02/1M tokens | API (cloud) |
| **OpenAI text-embedding-3-large** | 3.072 | Excelente | $0.13/1M tokens | API (cloud) |
| **BGE-M3 (BAAI)** | variable (hasta 8192 tokens) | Excelente (100+ idiomas) | **$0 (open source)** | Local (GPU recomendada) |
| **paraphrase-multilingual-MiniLM-L12-v2** | 384 | Bueno (50+ idiomas) | **$0 (open source)** | Local (CPU viable) |
| **Jina Embeddings v3** | variable | Excelente (modelo ES-EN bilingüe dedicado) | 1M tokens free, luego pago | API o local |
| **Cohere embed-multilingual-v3** | 1.024 | Excelente (100+ idiomas) | $0.10/1M tokens | API (cloud) |

**Recomendación por escenario:**

| Escenario | Modelo | Justificación |
|---|---|---|
| **Demo técnica** | `text-embedding-3-small` | Barato ($0.02/1M tokens), excelente calidad ES, sin infra de GPU. Para 50K documentos: ~$0.10 de coste total de embedding |
| **Sin dependencia de API** | `paraphrase-multilingual-MiniLM-L12-v2` | Gratuito, corre en CPU, 384 dims (compacto para DB). Calidad suficiente para turismo |
| **Máxima calidad open-source** | **BGE-M3** | State-of-the-art multilingüe. Soporta dense + sparse + ColBERT simultáneamente. Requiere GPU para embedding batch, pero queries pueden correr en CPU |
| **Producción con presupuesto** | `text-embedding-3-small` o Jina v3 | Balance calidad/coste. Jina tiene modelo bilingüe ES-EN específico |

#### 16.6.6 Arquitectura RAG Detallada — Schema de Base de Datos

```sql
-- PostgreSQL + pgvector schema

CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla principal de venues
CREATE TABLE venues (
    id              SERIAL PRIMARY KEY,
    external_id     TEXT UNIQUE,                -- OSM node_id, TUR4all ID, etc.
    name            TEXT NOT NULL,
    name_normalized TEXT NOT NULL,              -- lowercase, sin acentos
    city            TEXT NOT NULL,
    region          TEXT,                        -- Comunidad Autónoma
    country         TEXT DEFAULT 'ES',
    category        TEXT NOT NULL,              -- museum, restaurant, park, hotel, etc.
    subcategory     TEXT,                       -- tapas_bar, art_museum, etc.
    address         TEXT,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,

    -- Accesibilidad (estructura normalizada)
    wheelchair_access       TEXT,               -- 'yes', 'limited', 'no', 'unknown'
    wheelchair_parking      BOOLEAN,
    wheelchair_restroom     BOOLEAN,
    wheelchair_seating      BOOLEAN,
    tactile_paving          BOOLEAN,
    hearing_loop            BOOLEAN,
    sign_language           BOOLEAN,
    accessibility_score     FLOAT,              -- 0-10, calculado
    accessibility_source    TEXT,               -- 'tur4all', 'osm', 'google', 'manual'
    accessibility_detail    JSONB,             -- Detalle completo (tur4all profile, etc.)

    -- Metadatos
    description     TEXT,                       -- Descripción textual para embedding
    opening_hours   JSONB,
    pricing         JSONB,
    rating          FLOAT,
    review_count    INTEGER,
    photos          TEXT[],                     -- URLs
    website         TEXT,
    phone           TEXT,

    -- Fuentes y frescura
    sources         TEXT[] NOT NULL,            -- ['osm', 'tur4all', 'google']
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    data_quality    FLOAT DEFAULT 0.5,         -- 0-1, basado en completitud

    -- Vector embedding del texto descriptivo
    embedding       vector(1536),              -- Dimensión según modelo elegido

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_venues_city ON venues(city);
CREATE INDEX idx_venues_category ON venues(category);
CREATE INDEX idx_venues_wheelchair ON venues(wheelchair_access);
CREATE INDEX idx_venues_location ON venues USING gist (
    ll_to_earth(latitude, longitude)           -- Para búsquedas por radio
);
CREATE INDEX idx_venues_embedding ON venues USING hnsw (
    embedding vector_cosine_ops                -- Para búsqueda semántica
);

-- Tabla de rutas pre-calculadas (para venues populares)
CREATE TABLE cached_routes (
    id              SERIAL PRIMARY KEY,
    origin_venue_id INTEGER REFERENCES venues(id),
    dest_venue_id   INTEGER REFERENCES venues(id),
    mode            TEXT NOT NULL,              -- 'wheelchair', 'transit', 'walking'
    route_data      JSONB NOT NULL,            -- OpenRouteService/Google response
    duration_seconds INTEGER,
    accessibility_level TEXT,
    calculated_at   TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,

    UNIQUE(origin_venue_id, dest_venue_id, mode)
);

-- Vista materializada para búsqueda rápida
CREATE MATERIALIZED VIEW venue_search AS
SELECT
    v.id, v.name, v.city, v.category,
    v.wheelchair_access, v.accessibility_score,
    v.rating, v.description,
    v.embedding,
    -- Texto combinado para full-text search (backup de vector search)
    to_tsvector('spanish',
        coalesce(v.name, '') || ' ' ||
        coalesce(v.description, '') || ' ' ||
        coalesce(v.city, '') || ' ' ||
        coalesce(v.category, '')
    ) AS search_vector
FROM venues v
WHERE v.data_quality > 0.3;  -- Excluir datos de muy baja calidad
```

#### 16.6.7 Pipeline de Ingesta — Implementación

```python
# Estructura propuesta en el proyecto
integration/
├── data_ingestion/
│   ├── __init__.py
│   ├── base_ingestor.py          # ABC con interfaz común
│   ├── osm_ingestor.py           # Extrae POIs turísticos de PBF
│   ├── tur4all_ingestor.py       # Scrape + normalización
│   ├── opentripmap_ingestor.py   # API → descripciones Wikipedia
│   ├── government_ingestor.py    # datos.gob.es datasets
│   ├── google_enricher.py        # Enriquece venues con Google Places
│   ├── merger.py                 # Merge multi-fuente por geocoding
│   └── embedder.py               # Genera embeddings y actualiza DB
├── data_persistence/
│   ├── venue_repository.py       # CRUD + búsqueda vectorial
│   └── route_cache.py            # Cache de rutas calculadas
```

**Flujo de ingesta (ejecutable como script o cron job):**

```
1. OSM Extract (semanal)
   spain-latest.osm.pbf → pyrosm → filter tourism/amenity/leisure
   → normalize to VenueSchema → insert/update DB
   ~500K-1M venues, ~30 min procesamiento

2. TUR4all Scrape (mensual)
   tur4all.com → scrapy → parse fichas de accesibilidad
   → normalize → merge con venues existentes por geocoding
   ~4K venues, ~2h procesamiento

3. OpenTripMap Enrich (semanal)
   Por cada ciudad target → radius query → fetch descriptions
   → update venue.description con textos Wikipedia
   ~10K descriptions, ~1h procesamiento (rate limited)

4. Google Places Enrich (nightly, top venues)
   Top 100 venues por ciudad → Place Details
   → update wheelchair fields, reviews, horarios
   ~500 venues/noche, ~$2.50/noche

5. Embedding Generation (tras cada ingesta)
   Para venues nuevos/modificados → generar embedding del texto:
   "{name}. {category} en {city}. {description}.
    Accesibilidad: {wheelchair_access}. {accessibility_detail_summary}"
   → update venue.embedding

6. Materialized View Refresh
   REFRESH MATERIALIZED VIEW CONCURRENTLY venue_search;
```

#### 16.6.8 RAGSearchTool — Implementación

```python
class RAGSearchTool(BaseTool):
    """Busca venues relevantes en la base de conocimiento local."""

    name: str = "rag_venue_search"
    description: str = "Search accessible venues in the local knowledge base"

    async def _arun(self, context: ToolPipelineContext) -> ToolPipelineContext:
        # 1. Construir query semántica
        query_text = self._build_semantic_query(context)

        # 2. Generar embedding de la query
        query_embedding = await self.embedder.embed(query_text)

        # 3. Búsqueda vectorial + filtros
        results = await self.venue_repo.semantic_search(
            embedding=query_embedding,
            filters={
                "city": context.resolved_entities.destination,
                "category": self._intent_to_categories(context.nlu_result.intent),
                "wheelchair_access": self._get_wheelchair_filter(context),
            },
            limit=10,
            min_similarity=0.7
        )

        # 4. Convertir a PlaceCandidate
        context.candidates = [self._to_candidate(r) for r in results]

        # 5. Si pocos resultados, fallback a búsqueda full-text
        if len(context.candidates) < 3:
            fallback = await self.venue_repo.fulltext_search(
                query=query_text,
                city=context.resolved_entities.destination,
                limit=5
            )
            context.candidates.extend([self._to_candidate(r) for r in fallback])

        return context

    def _build_semantic_query(self, context: ToolPipelineContext) -> str:
        """Construye query optimizada para embedding similarity."""
        parts = [context.user_input]
        if context.nlu_result:
            parts.append(context.nlu_result.intent.replace("_", " "))
        if context.resolved_entities and context.resolved_entities.accessibility:
            parts.append(f"accesibilidad {context.resolved_entities.accessibility}")
        return " ".join(parts)
```

#### 16.6.9 Estimación de Volumen y Recursos

| Aspecto | Estimación |
|---|---|
| **Venues en DB (España completa)** | ~100K-500K (OSM) + 4K (TUR4all) + enrichment |
| **Tamaño embeddings (text-embedding-3-small, 1536 dims)** | ~500K × 1536 × 4 bytes = ~3 GB |
| **Tamaño total DB (PostgreSQL + pgvector)** | ~5-10 GB |
| **RAM requerida** | ~2-4 GB (HNSW index en memoria) |
| **Coste de embedding inicial** | ~$0.50-2.00 (text-embedding-3-small para 500K docs) |
| **Tiempo de ingesta inicial** | ~2-4 horas (OSM + TUR4all + embedding) |
| **Refresh incremental** | ~15-30 min/semana |

### 16.7 Enfoque Híbrido Recomendado (API + RAG)

Para este proyecto, la estrategia óptima es **combinar ambos enfoques**:

```
┌─────────────────────────────────────────────────────────────┐
│                    TOOL PIPELINE                             │
│                                                              │
│  ┌──────────────┐     ┌──────────────┐                      │
│  │ RAGSearchTool│     │ API Fallback │                      │
│  │ (primario)   │────▶│ (secundario) │                      │
│  │              │     │              │                      │
│  │ pgvector     │     │ Google Places│                      │
│  │ 100K+ venues │     │ (real-time)  │                      │
│  └──────┬───────┘     └──────┬───────┘                      │
│         │                    │                               │
│         └────────┬───────────┘                               │
│                  ▼                                            │
│         Merge + Dedup (por geocoding/name similarity)        │
│                  │                                            │
│                  ▼                                            │
│         AccessibilityEnrichment                              │
│         (RAG tiene datos TUR4all,                            │
│          Google aporta wheelchair fields frescos)             │
│                  │                                            │
│                  ▼                                            │
│         ProfileRanking → Directions → LLM                    │
└─────────────────────────────────────────────────────────────┘
```

**Flujo:**
1. **RAGSearchTool** busca primero en la DB local (latencia: 10-50ms)
2. Si los resultados son insuficientes (<3 venues) o de baja calidad, **Google Places API** como fallback
3. Merge de resultados eliminando duplicados
4. **AccessibilityEnrichment** combina datos de TUR4all (del RAG) + Google Places (wheelchair fields)
5. Ranking por perfil → Directions → LLM synthesis

**Ventajas del híbrido:**
- Latencia baja para la mayoría de queries (RAG local)
- Datos verificados de accesibilidad (TUR4all vía RAG)
- Datos frescos cuando se necesitan (Google API bajo demanda)
- Coste bajo (pocas llamadas a APIs)
- Funciona offline para datos ya indexados

### 16.8 Decisiones Pendientes para el Equipo

Antes de proceder con la implementación de Fase 1, es necesario decidir:

| # | Decisión | Opciones | Recomendación |
|---|---|---|---|
| D1 | **¿API-first o RAG-first?** | A: Empezar con Google APIs, añadir RAG después. B: Empezar con RAG, usar APIs para enriquecer | **A** para demo rápida, **B** si se prioriza control de datos y coste cero |
| D2 | **¿Qué vector DB?** | pgvector (unificado), LanceDB (embedded), Qdrant (dedicado) | **LanceDB** para demo, **pgvector** si se añade PostgreSQL |
| D3 | **¿Qué modelo de embedding?** | OpenAI small ($0.02/1M), BGE-M3 (free, GPU), MiniLM (free, CPU) | **OpenAI small** para demo (simple), **MiniLM** si se quiere zero-cost |
| D4 | **¿Routing wheelchair?** | Google Routes (transit), OpenRouteService (walking/wheelchair), ambos | **Ambos** — Google para transit, ORS para walking. Son complementarios |
| D5 | **¿Contactar PREDIF/TUR4all?** | Scrape vs partnership formal | **Partnership** recomendado. Scrape como Plan B |
| D6 | **¿Ciudades iniciales?** | Solo Madrid, Madrid+Barcelona, España completa | **Madrid+Barcelona** para demo (valida multi-ciudad sin overhead excesivo) |
| D7 | **¿Frecuencia de refresh RAG?** | Diario, semanal, mensual | **Semanal** para OSM, **mensual** para TUR4all, **nightly** para Google enrichment |

---

**Fin del documento.**

**Autor:** Principal Software Architect Audit
**Fecha:** 03 Marzo 2026
**Próxima revisión:** Al completar Fase 0
