# SDD Analysis: User Profile Preferences — POC to Production

**Fecha:** 20 de Febrero de 2026
**Versión:** 1.0
**Feature:** F3 — User Preference Profiles & Agent Specialization
**Metodología:** Specification-Driven Development (SDD)
**Branch:** `feature/implement-user-profile-preferences`

---

## 4.1 Análisis Arquitectónico

### a) Encaje de arquitectura actual vs documentación vs roadmap

#### As-Is (implementación real en repositorio)

| Componente | Ubicación real | Estado |
|-----------|---------------|--------|
| UI Selector de perfiles | `presentation/static/js/profiles.js` + modal dinámico | ✅ Implementado |
| Profile Registry (SSOT) | `presentation/static/config/profiles.json` (5 perfiles) | ✅ Implementado |
| ProfileService (resolución) | `application/services/profile_service.py` | ✅ Implementado |
| Chat endpoint (recibe profile) | `application/api/v1/chat.py:52-54` | ✅ Implementado |
| BackendAdapter (pasa profile) | `application/orchestration/backend_adapter.py:60-67` | ✅ Implementado |
| Prompt injection (directives) | `business/domains/tourism/prompts/response_prompt.py:24-50` | ✅ Implementado |
| Ranking bias aplicado en tools | No existe | ❌ No implementado |
| Tools profile-aware | No existe | ❌ No implementado |
| JSON extraction robusta | `business/domains/tourism/agent.py:181-221` (regex) | ⚠️ Frágil |
| Tests de perfiles | No existe | ❌ No implementado |

#### Gaps documentación ↔ repositorio

| # | Gap | Doc afectado | Código afectado | Impacto |
|---|-----|-------------|----------------|---------|
| G1 | `API_REFERENCE.md` no documenta `user_preferences` en request de chat ni `tourism_data`/`pipeline_steps`/`intent`/`entities` en response | `API_REFERENCE.md:125-150` | `application/models/requests.py` (UserPreferences, ChatMessageRequest) y `responses.py` (ChatResponse con tourism_data, pipeline_steps) | 🔴 Alto — contrato SSOT desactualizado, consumidores no pueden confiar en la spec |
| G2 | `API_REFERENCE.md` muestra `BackendInterface.process_query(transcription: str)` sin `active_profile_id` | `API_REFERENCE.md:278` | `shared/interfaces/interfaces.py:39` ya incluye `active_profile_id: Optional[str] = None` | 🟡 Medio — la interfaz real ya soporta profiles pero la doc no lo refleja |
| G3 | `API_REFERENCE.md` indica que `ConversationInterface` la implementa `integration/data_persistence/conversation_repository.py::ConversationService` | `API_REFERENCE.md:284` | La implementación real está en `application/services/conversation_service.py` | 🟡 Medio — documentación apunta a ubicación incorrecta |
| G4 | `ESTADO_ACTUAL_SISTEMA.md` referencia método `get_profile_by_id()` | `ESTADO_ACTUAL_SISTEMA.md:43` | Método real es `resolve_profile()` en `ProfileService` | 🟢 Bajo — inconsistencia de naming en documentación |
| G5 | `REFACTOR_PLAN` referencia método `get_profile_context()` que no existe | `REFACTOR_PLAN:833-873` | Método real es `resolve_profile()` que retorna `{id, label, prompt_directives, ranking_bias}` | 🟡 Medio — plan de refactor basado en API inexistente |
| G6 | `User_Profile_Preferences.md` usa "Capa 1/2/3" pero la arquitectura real tiene 5 capas | `User_Profile_Preferences.md` secciones 2-4 | Arquitectura real: Presentation, Application, Business, Integration, Shared | 🟢 Bajo — confusión de nomenclatura, sin impacto funcional |

#### Asunciones de POC que impiden producción

| Asunción | Evidencia | Riesgo producción |
|----------|-----------|-------------------|
| **Tools con mock data** | `business/domains/tourism/data/venue_data.py` (4 venues hardcodeados), `nlu_patterns.py` (10 destinos) | 🔴 Crítico — sistema no escala fuera de Madrid |
| **Conversation history in-memory** | `MultiAgentOrchestrator.conversation_history` (lista en instancia), `ConversationService` (dict en memoria) | 🔴 Crítico — se pierde al reiniciar, no soporta concurrencia |
| **Sin autenticación** | `settings.auth_enabled=False`, `AuthInterface` sin implementación | 🔴 Crítico — sin user_id no hay persistencia de preferencias por usuario |
| **Sin retry/timeout en LLM** | `orchestrator.py:53` llama `self.llm.invoke(prompt)` sin timeout ni retry | 🟡 Alto — llamada bloqueante sin protección |
| **Sin observabilidad de costes LLM** | No hay tracking de tokens consumidos ni coste por request | 🟡 Alto — coste impredecible en producción |
| **CORS permisivo** | `settings.py`: `cors_origins=["*"]` en dev | 🟡 Medio — necesita restricción en producción |
| **Sin rate limiting** | No hay middleware de rate limiting | 🟡 Medio — vulnerable a abuso |
| **Sin validación de tamaño de input** | `ChatMessageRequest.message` sin `max_length` en Pydantic model | 🟡 Medio — prompt injection y costes |
| **Sin idempotencia** | Cada request crea nuevo `conversation_id` si no se envía | 🟢 Bajo — aceptable en POC |
| **Sin versionado de API** | Prefijo `/api/v1` existe pero sin strategy de deprecation | 🟢 Bajo — aceptable en POC |

---

### b) Capas que participan

#### Mapa de componentes por capa

```
┌─────────────────────────────────────────────────────────────────────┐
│ PRESENTATION                                                        │
│ Responsabilidades: Render HTML, servir assets, UI modal perfiles    │
│ Boundaries: Solo consume API REST, no importa capas internas        │
│ Dependencias permitidas: → Shared (tipos), → CDN (Bootstrap)       │
│ Componentes:                                                        │
│   fastapi_factory.py      ← App factory, routes, exception handler │
│   server_launcher.py      ← Startup uvicorn                        │
│   templates/index.html    ← SPA Bootstrap + Jinja2                 │
│   static/js/profiles.js   ← ProfileManager (modal, LocalStorage)   │
│   static/js/chat.js       ← ChatHandler (envía user_preferences)   │
│   static/js/cards.js      ← CardRenderer (renderiza tourism_data)  │
│   static/js/app.js        ← Coordinator (init ProfileManager)      │
│   static/config/profiles.json ← SSOT Profile Registry              │
│                                                                     │
│ ⚠ VIOLACIÓN: profiles.json es cargado por ProfileService           │
│   (Application layer) vía file path directo                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│ APPLICATION                                                         │
│ Responsabilidades: API endpoints, orchestration, DTOs, services     │
│ Boundaries: Expone REST, consume Business via BackendInterface      │
│ Dependencias permitidas: → Business (via interfaces), → Shared      │
│ Componentes:                                                        │
│   api/v1/chat.py          ← POST /chat/message (extrae profile_id) │
│   api/v1/audio.py         ← POST /audio/transcribe                 │
│   api/v1/health.py        ← Health checks                          │
│   models/requests.py      ← UserPreferences, ChatMessageRequest    │
│   models/responses.py     ← ChatResponse, TourismData, Venue, etc. │
│   orchestration/backend_adapter.py ← LocalBackendAdapter           │
│   services/profile_service.py     ← ProfileService (carga JSON)    │
│   services/conversation_service.py ← In-memory conversations       │
│   services/audio_service.py        ← Audio processing              │
│                                                                     │
│ ⚠ VIOLACIÓN: ProfileService importa file de Presentation layer     │
│ ⚠ VIOLACIÓN: backend_adapter.py importa TourismMultiAgent (concreto│
│   de Business) — debería usar interfaz de Shared                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│ BUSINESS                                                            │
│ Responsabilidades: Multi-agent orchestration, domain logic, prompts │
│ Boundaries: Recibe query + profile_context, retorna AgentResponse   │
│ Dependencias permitidas: → Shared (interfaces, exceptions)          │
│ Componentes:                                                        │
│   core/orchestrator.py    ← MultiAgentOrchestrator (Template Method)│
│   core/interfaces.py      ← MultiAgentInterface ABC                │
│   core/models.py          ← AgentResponse dataclass                │
│   core/canonicalizer.py   ← Normalización tourism_data → SSOT      │
│   domains/tourism/agent.py     ← TourismMultiAgent (4 tools+LLM)   │
│   domains/tourism/prompts/     ← system_prompt.py, response_prompt │
│   domains/tourism/tools/       ← NLU, Accessibility, Route, Info   │
│   domains/tourism/data/        ← Mock data (venue_data, route_data)│
│                                                                     │
│ ⚠ NOTA: ranking_bias recibido pero NO consumido en ningún tool     │
│ ⚠ NOTA: Tools heredan de langchain.BaseTool (acoplamiento fuerte)  │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│ INTEGRATION                                                         │
│ Responsabilidades: APIs externas, config, persistencia              │
│ Boundaries: Adapta servicios externos a interfaces internas         │
│ Dependencias permitidas: → Shared (interfaces), → External APIs     │
│ Componentes:                                                        │
│   configuration/settings.py   ← Pydantic Settings (.env)           │
│   external_apis/stt_factory.py     ← Factory para STT services     │
│   external_apis/azure_stt_client.py ← Azure Speech implementation  │
│   external_apis/whisper_services.py ← Whisper implementations      │
│   external_apis/stt_agent.py        ← STT coordination agent       │
│   data_persistence/conversation_repository.py ← (interface only?)  │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│ SHARED (Cross-Cutting)                                              │
│ Responsabilidades: Interfaces, exceptions, DI, utilidades           │
│ Boundaries: Importado por TODAS las capas, no importa ninguna       │
│ Dependencias permitidas: → Ninguna (solo stdlib + pydantic)         │
│ Componentes:                                                        │
│   interfaces/interfaces.py  ← BackendInterface, ConversationIfc    │
│   interfaces/stt_interface.py ← STTServiceInterface                │
│   exceptions/exceptions.py   ← Jerarquía de excepciones            │
│   utils/dependencies.py      ← FastAPI DI functions                │
│                                                                     │
│ ⚠ VIOLACIÓN CRÍTICA: dependencies.py importa clases concretas de  │
│   Application layer (LocalBackendAdapter, AudioService,             │
│   ConversationService). Shared NO debe depender de Application.     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### c) Flujo completo de datos (end-to-end)

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. FRONTEND (profiles.js + chat.js)                                    │
│                                                                        │
│ ProfileManager.getProfileForRequest()                                  │
│   → {active_profile_id: "night_leisure"} (de LocalStorage)            │
│                                                                        │
│ ChatHandler.sendMessage(text)                                          │
│   → POST /api/v1/chat/message                                         │
│     Body: {                                                            │
│       "message": "Recomiéndame actividades en Madrid",                │
│       "conversation_id": "conv_123",                                   │
│       "user_preferences": {"active_profile_id": "night_leisure"}      │
│     }                                                                  │
└──────────────────────────┬─────────────────────────────────────────────┘
                           │ HTTP POST (JSON)
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. CHAT ENDPOINT (chat.py:31-86)                                       │
│                                                                        │
│ request: ChatMessageRequest (Pydantic validation)                      │
│   → active_profile_id = request.user_preferences.active_profile_id    │
│   → backend_service.process_query(                                     │
│       transcription=message,                                           │
│       active_profile_id="night_leisure"                                │
│     )                                                                  │
└──────────────────────────┬─────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. BACKEND ADAPTER (backend_adapter.py:60-184)                         │
│                                                                        │
│ profile_context = ProfileService.resolve_profile("night_leisure")      │
│   → Carga profiles.json (una vez, cache clase)                         │
│   → Retorna: {id, label, prompt_directives, ranking_bias}             │
│                                                                        │
│ if use_real_agents:                                                     │
│   → _process_real_query(transcription, profile_context)                │
│ else:                                                                   │
│   → ✅ _simulate_ai_response(transcription, profile_context)           │
└──────────────────────────┬─────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. TOURISM MULTI-AGENT (agent.py via orchestrator.py)                  │
│                                                                        │
│ process_request_sync(user_input, profile_context):                     │
│                                                                        │
│   4a. ✅ _execute_pipeline(user_input):  RECIBE profile_context      │
│       NLU Tool._run(user_input)       → JSON string (regex-based NLU) │
│       Accessibility._run(nlu_raw)     → JSON string (ACCESSIBILITY_DB)│
│       Route._run(accessibility_raw)   → JSON string (ROUTE_DB)        │
│       TourismInfo._run(nlu_raw)       → JSON string (VENUE_DB)        │
│       → tool_results: dict[str, str]                                   │
│       → metadata: {pipeline_steps, tourism_data, intent, entities}    │
│                                                                        │
│   4b. _build_response_prompt(user_input, tool_results, profile_context)│
│       → Inyecta prompt_directives + ranking_bias como TEXTO           │
│       → "PERFIL ACTIVO: Ocio nocturno\n Directivas: ..."             │
│       → Pide PARTE 1 (texto) + PARTE 2 (JSON block)                  │
│                                                                        │
│   4c. llm.invoke(prompt) → GPT-4 response (text + optional JSON)     │
│                                                                        │
│   4d. _extract_structured_data(llm_text, metadata):                    │
│       → regex: r"```json\s*(\{.*?\})\s*```"                          │
│       → Si match: parse JSON → canonicalize → merge into metadata     │
│       → Si no match: tourism_data queda como tool data o null         │
│                                                                        │
│   → AgentResponse(response_text, tool_results, metadata)              │
└──────────────────────────┬─────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 5. RESPONSE VALIDATION (backend_adapter.py:142-161)                    │
│                                                                        │
│ tourism_data → TourismData.parse_obj() (Pydantic)                      │
│   → Si válido: structured_response["tourism_data"] = td.dict()        │
│   → Si inválido: log warning, tourism_data = null (graceful degrad.)  │
│                                                                        │
│ pipeline_steps → PipelineStep.parse_obj() por cada step               │
│   → Si inválido: skip step pero continuar                              │
└──────────────────────────┬─────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 6. FRONTEND RENDER (chat.js + cards.js)                                │
│                                                                        │
│ ChatResponse JSON → addAssistantMessage(ai_response)                   │
│ if (tourism_data) → CardRenderer.render(tourism_data)                  │
│   → Venue card + Accessibility card + Route cards                      │
│ if (pipeline_steps) → PipelineRenderer.render(pipeline_steps)          │
│   → Pipeline visualization steps                                       │
│                                                                        │
│ Telemetría: Ninguna (no hay logging frontend)                          │
└────────────────────────────────────────────────────────────────────────┘
```

**Puntos de quiebre identificados:**

1. ✅ **`_execute_pipeline()` no recibe `profile_context`** → tools no pueden priorizar por perfil
2. **Tools usan mock data estático** → mismos resultados independientemente de la query
3. **JSON extraction regex** → `tourism_data = null` en ~60% de los casos
4. ✅ **Simulation mode ignora profile** → demo no refleja comportamiento de perfiles

---

### d) Puntos de acoplamiento

| # | Acoplamiento | Tipo | Ubicación | Impacto | Riesgo | Refactor target |
|---|-------------|------|-----------|---------|--------|----------------|
| C1 | `dependencies.py` importa clases concretas de Application | Direct coupling, violación Clean Architecture | `shared/utils/dependencies.py:5-8` | 🔴 Alto — Shared depende de Application | Circular dependency si se extiende | Mover DI setup a Presentation o Application |
| C2 | `ProfileService` lee archivo de Presentation layer | File system coupling, violación de capas | `application/services/profile_service.py:31-37` | 🟡 Medio — Application acoplada a Presentation | Falla si se cambia ubicación de static files | Servir profiles.json via endpoint o inyectar path via Settings |
| C3 | `backend_adapter.py` importa `TourismMultiAgent` directamente | Concrete dependency | `backend_adapter.py:38` (lazy import) | 🟡 Medio — Application acoplada a implementación concreta de Business | No se puede intercambiar dominio sin modificar adapter | Usar `MultiAgentInterface` como tipo + factory/DI |
| C4 | Tools heredan de `langchain.BaseTool` | Framework coupling | `business/domains/tourism/tools/*.py` | 🟡 Medio — Domain tools acoplados a framework LangChain | Migrar de framework requiere reescribir todos los tools | Crear interfaz propia `ToolInterface` en Shared, adaptar LangChain en Integration |
| C5 | `response_prompt.py` embebe schema JSON como string literal | Schema coupling | `response_prompt.py:3-21` | 🟡 Medio — Schema duplicado entre prompt y Pydantic models | Desincronización si se cambia el schema | Generar schema prompt desde Pydantic model |
| C6 | `canonicalizer.py` importa `TourismData` de Application models | Layer violation | `business/core/canonicalizer.py` | 🟡 Medio — Business depende de Application | Acoplamiento ascendente | Mover `TourismData` a Shared o Business models |
| C7 | `agent.py` usa `canonicalize_tourism_data()` que depende de Pydantic models de Application | Transitive dependency | `business/domains/tourism/agent.py:11` | 🟡 Medio — Mismo que C6 | Mismo que C6 | Mismo que C6 |
| C8 | Frontend `chat.js` acopla formato de request a estructura interna | UI-backend contract | `presentation/static/js/chat.js` | 🟢 Bajo — Aceptable via contrato REST | Cambio de API rompe frontend | Versionado de API + contrato documentado |

---

### e) Riesgos técnicos

| # | Riesgo | Severidad | Probabilidad | Impacto |
|---|--------|-----------|-------------|---------|
| R1 | **Tools son stubs con mock data** — sistema no funciona fuera de 4 venues Madrid | 🔴 Alta | Certeza | Todo el pipeline de datos es decorativo |
| R2 | **JSON extraction regex-based** — `tourism_data = null` en ~60% de respuestas | 🔴 Alta | Alta | UI no puede renderizar Rich Cards |
| R3 | **ranking_bias nunca consumido** — perfil solo cambia tono textual, no datos | 🔴 Alta | Certeza | Feature F3 no cumple su promesa de negocio |
| R4 | **Sin tests** — directorio `tests/` vacío (solo `__init__.py` y `conftest.py`) | 🔴 Alta | Certeza | Cualquier refactor puede romper funcionalidad sin detección |
| R5 | **Conversación in-memory** — se pierde al reiniciar, race conditions con concurrencia | 🟡 Media | Alta en producción | Pérdida de contexto conversacional |
| R6 | **Sin timeout/retry en LLM** — `llm.invoke()` sin protección | 🟡 Media | Media | Requests colgados, mala UX |
| R7 | **Coste LLM no monitoreado** — sin tracking de tokens/coste | 🟡 Media | Certeza en producción | Facturación impredecible |
| R8 | **PII en logs** — queries de usuario se loguean en plano (`backend_adapter.py:73`) | 🟡 Media | Alta | Compliance issues (GDPR) |
| R9 | **CORS permisivo** (`*`) | 🟡 Media | Baja en POC | Vulnerabilidad en producción |
| R10 | **Sin rate limiting** | 🟡 Media | Media en producción | Abuso de API, coste LLM desbocado |
| R11 | **Dependencia de OpenAI API** — single provider sin fallback | 🟡 Media | Baja | Indisponibilidad total si OpenAI cae |
| R12 | **Function calling deprecated syntax** en REFACTOR_PLAN (`functions=`, `function_call=`) | 🟢 Baja | Certeza al implementar | Necesita usar `tools=` y `tool_choice=` |

---

### f) Riesgos de regresión

| Ruta crítica | Qué puede romperse | Por qué |
|-------------|-------------------|---------|
| **Chat endpoint** (`POST /chat/message`) | Si se modifica `ChatMessageRequest` o `ChatResponse` | Cambio de contrato rompe frontend + tests (si existiesen) |
| **Pipeline de tools** (NLU→Acc→Route→Info) | Si se modifica signature de `BaseTool._run()` | LangChain espera `_run(self, input: str)` — añadir parámetros rompe la cadena |
| **Prompt builder** | Si se modifica `response_prompt.py` | LLM puede dejar de emitir JSON block → `tourism_data = null` |
| **Canonicalizer** | Si se modifica `TourismData` Pydantic model | Validación más estricta puede rechazar datos que antes pasaban |
| **Simulation mode** | Si se refactoriza `_simulate_ai_response()` | Demo UI depende de respuestas hardcodeadas para funcionar |
| **Profile flow** | Si se cambia `profiles.json` schema | Frontend (ProfileManager) y backend (ProfileService) deben estar sincronizados |

---

### g) Estrategia de mitigación

#### Estrategia general: Strangler Fig + Feature Flags

Cada fase del refactor introduce la nueva implementación **junto a** la existente, controlada por feature flag en `Settings`. Solo cuando la nueva versión está validada se elimina la antigua.

```python
# integration/configuration/settings.py
class Settings(BaseSettings):
    # Feature flags para refactor incremental
    use_real_tools: bool = Field(default=False)       # Fase 0
    use_function_calling: bool = Field(default=False)  # Fase 2
    use_profile_ranking: bool = Field(default=False)   # Fase 3
```

#### Tabla Riesgo → Mitigación → Señal de detección

| Riesgo | Mitigación | Señal de detección |
|--------|-----------|-------------------|
| R1 Tools stubs | Fase 0: Implementar tools con APIs reales (Google Maps, spaCy). Feature flag: `use_real_tools` | Test: query "Alhambra Granada" → `tourism_data.venue.name` contiene "Alhambra" |
| R2 JSON regex | Fase 2: Usar `structured_output` (OpenAI response_format=json_object) o function calling con `tools=` | Métrica: `tourism_data_null_rate < 5%` (actualmente ~60%) |
| R3 ranking_bias no usado | Fase 3: Implementar `_apply_profile_ranking()` en agent.py | Test: misma query + perfil `night_leisure` vs `cultural` → diferente orden de venues |
| R4 Sin tests | Fase 0: Crear test suite mínima antes de cualquier refactor | CI: `pytest --cov > 60%` antes de merge |
| R5 In-memory state | Fase 2+: Migrar a Redis/SQLite para conversaciones | Health check: restart container → conversations persist |
| R6 Sin timeout LLM | Fase 1: Añadir `timeout=30` y `max_retries=2` a ChatOpenAI | Log: `llm_timeout_count` metric |
| R7 Coste LLM | Fase 1: LangChain callbacks para tracking tokens | Dashboard: coste diario LLM < threshold |
| R8 PII en logs | Fase 1: Redactar queries en logs (hash o truncar) | Audit: grep logs por datos personales = 0 hits |
| R12 Deprecated syntax | Usar `tools=` y `tool_choice=` en implementación | CI: no `functions=` ni `function_call=` en codebase |

---

## 4.2 Plan de Implementación

### a) Archivos nuevos

| Ruta | Responsabilidad |
|------|----------------|
| `shared/interfaces/profile_interface.py` | Interfaz `ProfileResolverInterface` para desacoplar ProfileService |
| `shared/interfaces/tool_interface.py` | Interfaz `DomainToolInterface` para desacoplar de `langchain.BaseTool` |
| `business/core/ranking.py` | `ProfileRankingPolicy` — lógica de ranking por perfil (Strategy pattern) |
| `business/core/structured_output.py` | Extracción de JSON estructurado via function calling / structured output |
| `integration/external_apis/google_maps_client.py` | Adapter Google Places + Directions API (Fase 0) |
| `tests/test_business/test_profile_ranking.py` | Tests unitarios para ranking por perfil |
| `tests/test_business/test_canonicalizer.py` | Tests unitarios para canonicalizador |
| `tests/test_business/test_tourism_agent.py` | Tests integración para pipeline completo |
| `tests/test_application/test_profile_service.py` | Tests unitarios ProfileService |
| `tests/test_application/test_backend_adapter.py` | Tests unitarios BackendAdapter |
| `tests/fixtures/profile_test_cases.json` | Golden outputs por perfil para regression tests |

### b) Archivos modificados

| Ruta | Motivo del cambio |
|------|-------------------|
| ✅ `application/orchestration/backend_adapter.py` | Pasar `profile_context` al pipeline completo, no solo al prompt |
| `application/services/profile_service.py` | Implementar interfaz, enriquecer con `expected_types` |
| ✅ `business/domains/tourism/agent.py` | `_execute_pipeline()` recibe profile_context, nuevo `_apply_profile_ranking()` |
| ✅ `business/core/orchestrator.py` | Pasar `profile_context` a `_execute_pipeline()` (signature change) |
| `business/core/canonicalizer.py` | Tolerancia a partial data, mejor logging |
| `business/domains/tourism/prompts/response_prompt.py` | Opción: separar prompt texto-only vs structured output prompt |
| `business/domains/tourism/tools/*_tool.py` | Fase 4: Añadir context awareness (no via `_run` signature — ver sección Diseño) |
| `integration/configuration/settings.py` | Añadir feature flags para refactor incremental |
| `shared/utils/dependencies.py` | Mover imports concretos, usar factory pattern |
| `documentation/API_REFERENCE.md` | Actualizar contrato con `user_preferences`, `tourism_data`, `pipeline_steps` |

### c) Clases nuevas

| Clase | Responsabilidad |
|-------|----------------|
| `ProfileRankingPolicy` | Aplica `ranking_bias` sobre resultados de tools para reordenar venues (Strategy) |
| `StructuredOutputExtractor` | Extrae JSON de LLM via structured output / function calling con retry |
| `ProfileResolverInterface` (ABC) | Contrato para resolución de perfiles (permite mock en tests) |
| `DomainToolInterface` (ABC) | Contrato agnóstico de framework para tools de dominio |
| `GoogleMapsAdapter` | Adapter para Google Places + Directions API |

### d) Interfaces o contratos nuevos

| Interface/Contract | Propósito | Boundary |
|-------------------|-----------|----------|
| `ProfileResolverInterface` | Desacoplar resolución de perfiles de implementación JSON file | Shared → Application |
| `DomainToolInterface` | Desacoplar tools de LangChain BaseTool | Shared → Business |
| `ExternalDataSourceInterface` | Contrato para fuentes de datos de venues/rutas | Shared → Integration |
| Actualización `API_REFERENCE.md` ChatRequest/Response | Documentar `user_preferences` y `tourism_data` | Presentation ↔ Application |

### e) Dependencias introducidas (justificadas)

| Nombre | Por qué es necesaria | Alternativa descartada | Impacto operativo |
|--------|---------------------|----------------------|------------------|
| `googlemaps` | APIs reales para venues y rutas (Fase 0) | Scraping web (frágil, ToS issues) | API key requerida, coste por request (~$5/1000 req) |
| `spacy` + `es_core_news_md` | NER real en español para NLU tool (Fase 0) | Regex mejorado (limitado, no escala) | ~100MB modelo, startup más lento |
| `pytest` + `pytest-asyncio` | Tests (ya en devDependencies pero sin tests) | unittest (menos ergonómico) | Solo dev, sin impacto producción |
| `pytest-cov` | Cobertura de tests | Manual (propenso a olvido) | Solo dev |

### f) Roadmap por fases (POC → Producción)

---

#### Fase 0: Estabilización — Contratos, Tests, Observabilidad

**Objetivo:** Establecer la base que permite refactorizar sin romper nada.

**Entregables:**
1. `API_REFERENCE.md` actualizado con contratos reales (user_preferences, tourism_data, pipeline_steps)
2. Test suite mínima: ≥15 tests cubriendo flujo crítico (chat endpoint, ProfileService, canonicalizer, pipeline)
3. Feature flags en Settings para control de refactor
4. Fix violación de capas: mover DI setup de Shared a Application
5. Structured logging con correlation_id por request

**Riesgos:**
- Tests pueden revelar bugs existentes no conocidos
- Actualizar API_REFERENCE puede exponer incompatibilidades con frontend

**Criterio de salida verificable:**
- [ ] `API_REFERENCE.md` refleja 100% de campos reales en Request/Response
- [ ] `pytest` ejecuta ≥15 tests, todos pasan
- [ ] Feature flags `use_real_tools`, `use_function_calling`, `use_profile_ranking` en Settings
- [ ] `dependencies.py` no importa clases concretas de Application directamente
- [ ] Cada request tiene `correlation_id` en logs

---

#### Fase 1: Canonización Robusta + Protección LLM

**Objetivo:** `tourism_data` nunca es `null` si hay datos disponibles. LLM calls protegidas.

**Entregables:**
1. `canonicalizer.py` con tolerancia a partial data, string-to-dict conversion, mejor logging
2. `ChatOpenAI` con `timeout=30`, `max_retries=2`
3. LLM token/cost tracking via callbacks
4. PII redaction en logs

**Riesgos:**
- Canonicalizador más tolerante puede aceptar datos de baja calidad
- Timeout puede interrumpir respuestas válidas pero lentas

**Criterio de salida verificable:**
- [ ] `tourism_data_null_rate < 20%` (desde ~60% actual)
- [ ] Timeout test: LLM call > 30s → error manejado gracefully
- [ ] Logs no contienen PII (audit grep)
- [ ] Token count visible en structured log por request

---

#### Fase 2: Extracción Estructurada Determinista

**Objetivo:** JSON output garantizado via structured output (no regex).

**Entregables:**
1. `StructuredOutputExtractor` usando `response_format={"type": "json_object"}` o LangChain `with_structured_output()`
2. Separar o mantener single LLM call pero con structured output forzado
3. Retry con fallback: structured output → regex legacy → tool data
4. Eliminar regex extraction como path principal (mantener como fallback)

**Riesgos:**
- `response_format=json_object` puede no soportar schema complejo
- Doble LLM call aumenta coste y latencia (~2x)
- LangChain `with_structured_output()` requiere Pydantic model compatible

**Criterio de salida verificable:**
- [ ] `tourism_data_null_rate < 5%`
- [ ] No regex en path principal de extracción JSON
- [ ] Latencia p95 < 15s (monitoreada)
- [ ] Tests: 10 queries diversas → 10 tourism_data válidos

---

#### Fase 3: Profile-Driven Ranking Real

**Objetivo:** `ranking_bias` afecta el orden y priorización de resultados.

**Entregables:**
1. `ProfileRankingPolicy` en `business/core/ranking.py`
2. Aplicación de ranking post-pipeline, pre-LLM
3. Métricas de profile impact (% match entre venue_type y expected_types)
4. Integration test: misma query + perfiles diferentes → venues en orden diferente

**Riesgos:**
- Ranking con mock data no aporta valor real (dependencia de Fase 0 para tools reales)
- Ranking puede sesgar demasiado si bias muy agresivos

**Criterio de salida verificable:**
- [ ] Test: `"actividades Madrid"` + `night_leisure` → primer venue type es `entertainment` o `nightclub`
- [ ] Test: `"actividades Madrid"` + `cultural` → primer venue type es `museum`
- [ ] Métrica `profile_venue_type_match_rate > 70%`
- [ ] Log por request: `ranking_applied=true`, `profile_id`, `venue_order_changed`

---

#### Fase 4: Tools con Datos Reales (Prerequisito para producción)

**Objetivo:** Tools devuelven datos reales, no mock data.

**Entregables:**
1. NLU Tool con spaCy NER (reemplaza regex matching)
2. Accessibility/Route/Info Tools con Google Maps API (o alternativa RAG)
3. Anti-corruption layer: normalizar respuestas externas a schema interno
4. Cache layer para reducir API calls (TTL-based)
5. Error handling: rate limits, timeouts, fallbacks a datos cached

**Riesgos:**
- APIs externas añaden latencia y coste
- Rate limits pueden bloquear servicio en horas punta
- Calidad de datos de APIs varía por región/venue

**Criterio de salida verificable:**
- [ ] Query "Alhambra Granada" → `venue.name` contiene "Alhambra"
- [ ] Query "Catedral Sevilla" → rutas reales desde punto de origen
- [ ] Funciona para ≥5 ciudades españolas sin hardcoding
- [ ] Fallback: si API externa falla → usa datos cached + log warning
- [ ] `tourism_data` con datos reales en ≥90% de queries

---

#### Fase 5: Hardening + Rollout

**Objetivo:** Sistema listo para tráfico real.

**Entregables:**
1. Rate limiting middleware
2. Auth stub reemplazado por implementación real (OAuth2 / API key)
3. Conversación persistida en SQLite/Redis
4. CORS configurado por entorno
5. Monitoring dashboard (latencia, error rate, coste LLM, profile distribution)
6. Eliminar legacy: simulation mode, archivos huérfanos en root

**Riesgos:**
- Auth puede romper frontend existente
- Migración de in-memory a persistent state requiere migration path

**Criterio de salida verificable:**
- [ ] Rate limit: >100 req/min → 429 response
- [ ] Auth: requests sin token → 401
- [ ] Container restart → conversations persisten
- [ ] CORS: solo dominios permitidos aceptados
- [ ] Archivos huérfanos (`langchain_agents.py`, `azure_test*.py`, `test_voiceflow.py`) eliminados
- [ ] Cobertura tests ≥ 70%

---

## 4.3 Diseño Técnico Detallado

### Backend

#### Cambios en modelos

**Modelos existentes y ubicación:**

| Modelo | Ubicación | Propósito |
|--------|-----------|-----------|
| `UserPreferences` | `application/models/requests.py` | DTO con `active_profile_id: Optional[str]` |
| `ChatMessageRequest` | `application/models/requests.py` | Request con `message`, `conversation_id`, `user_preferences` |
| `TourismData` | `application/models/responses.py` | Composite: `venue`, `routes`, `accessibility` |
| `Venue` | `application/models/responses.py` | Nombre, tipo, score, facilities, hours, pricing |
| `Route` | `application/models/responses.py` | Transport, line, duration, accessibility, cost, steps |
| `Accessibility` | `application/models/responses.py` | Level, score, certification, facilities, services |
| `ChatResponse` | `application/models/responses.py` | Response con `ai_response`, `tourism_data`, `pipeline_steps` |
| `AgentResponse` | `business/core/models.py` | Dataclass: `response_text`, `tool_results`, `metadata` |

**Cambios necesarios para producción:**

1. **Mover `TourismData`, `Venue`, `Route`, `Accessibility` a Shared layer** — actualmente en `application/models/responses.py` pero consumidos por `business/core/canonicalizer.py` (violación de capa). Propuesta: crear `shared/models/tourism.py`.

2. **Añadir `profile_applied` a `ChatResponse`** — para que el frontend pueda mostrar qué perfil afectó la respuesta:
   ```python
   class ChatResponse:
       profile_applied: Optional[dict] = None  # {id, label} o null
   ```

3. **Alinear con `API_REFERENCE.md`** — actualizar doc para reflejar campos `tourism_data`, `pipeline_steps`, `intent`, `entities`, `user_preferences` que ya existen en código pero no en spec.

#### Cambios en servicios

**Application services vs Business domain:**

| Servicio | Capa actual | Capa correcta | Notas |
|----------|------------|---------------|-------|
| `ProfileService` | Application | Application ✅ | Correcto como servicio de aplicación, pero necesita interfaz en Shared |
| `ConversationService` | Application | Application ✅ | OK, pero persistencia debería usar adapter de Integration |
| `AudioService` | Application | Application ✅ | Correcto |
| `LocalBackendAdapter` | Application | Application ✅ | Correcto como adapter, pero debería usar factory para instanciar Business |
| `ProfileRankingPolicy` | No existe | Business ✅ | Lógica de ranking = regla de negocio → vive en Business |
| `StructuredOutputExtractor` | No existe | Business ✅ | Lógica de extracción/validación de output LLM |

**Estrategia de ranking (Strategy pattern):**

```
ProfileRankingPolicy
├── apply_ranking(tourism_data, ranking_bias) → tourism_data (reordenado)
├── compute_venue_score(venue, ranking_bias) → float
└── get_impact_metrics() → dict  # para logging/observabilidad
```

La política vive en `business/core/ranking.py` y es invocada por `TourismMultiAgent._execute_pipeline()` después de ejecutar tools y antes de invocar LLM.

#### Cambios en adapters

**Anti-corruption layer para APIs externas (Fase 4):**

```
GoogleMapsAdapter (Integration layer)
├── search_venues(query, location, radius) → list[VenueRaw]
├── get_directions(origin, destination, mode) → list[RouteRaw]
└── get_place_details(place_id) → VenueDetailsRaw

↓ Normalización

DomainToolInterface (Shared)
├── execute(input, context) → ToolResult (dict canónico)
```

Las respuestas de Google Maps usan su propio schema (e.g. `wheelchair_accessible_entrance` como bool). El adapter normaliza esto al schema canónico (`accessibility_score`, `facilities[]`).

#### Validación de entrada/salida

**Boundary validations (DTO):**
- `ChatMessageRequest.message`: añadir `max_length=2000` (protección prompt injection + coste)
- `UserPreferences.active_profile_id`: validar contra regex `^[a-z_]{1,50}$` (solo IDs válidos)
- File upload: ya existe validación de formato/tamaño en AudioService

**Invariantes de dominio:**
- `ranking_bias` weights: 0.0 < weight ≤ 2.0 (evitar distorsión extrema)
- `accessibility_score`: 0.0 ≤ score ≤ 10.0
- `facilities` keys: validar contra set canónico (`CANONICAL_FACILITIES` en canonicalizer)

**Validación post-LLM:**
- JSON output: validar contra Pydantic `TourismData` model
- Facilities: solo keys canónicas aceptadas
- Scores: dentro de rango [0, 10]
- Venues: nombre no vacío

#### Manejo de errores

**Taxonomía de errores:**

| Categoría | Ejemplo | Handling | HTTP status |
|-----------|---------|----------|-------------|
| **Validación** | Message vacío, profile_id inválido | `ValidationException` → 400 | 400 |
| **Integración** | OpenAI timeout, Google Maps rate limit | `BackendCommunicationException` → retry + fallback | 502/503 |
| **Dominio** | Canonicalization fail, ranking fail | Log warning + graceful degradation (partial data) | 200 (con data parcial) |
| **LLM** | Response no parseable, hallucination | Retry structured output → fallback tool data → null | 200 (con data parcial) |
| **Infra** | DB down, settings invalid | `ConfigurationException` → 500 | 500 |

**Reintentos y timeouts:**
- LLM calls: `timeout=30s`, `max_retries=2`, backoff exponencial
- Google Maps API: `timeout=10s`, `max_retries=1`
- Canonicalization retry: 2 intentos (tool_data → llm_data → null)

**Circuit breakers:** No necesarios en POC. Considerar para producción con alto tráfico (>100 req/min).

#### Logging

**Structured logging (ya implementado parcialmente con structlog):**

```python
# Por cada request al chat endpoint:
logger.info(
    "chat_request_received",
    correlation_id=correlation_id,
    profile_id=active_profile_id or "none",
    message_length=len(message),  # NO el contenido
)

# Por cada tool execution:
logger.info(
    "tool_executed",
    correlation_id=correlation_id,
    tool_name="nlu",
    duration_ms=450,
    status="completed",
)

# Por cada LLM invocation:
logger.info(
    "llm_invocation",
    correlation_id=correlation_id,
    prompt_length=len(prompt),  # NO el contenido
    response_length=len(response),
    tokens_used=token_count,
    duration_ms=llm_duration_ms,
)

# Por cada profile ranking:
logger.info(
    "profile_ranking_applied",
    correlation_id=correlation_id,
    profile_id="night_leisure",
    ranking_applied=True,
    venue_order_changed=True,
    top_venue_type="entertainment",
)
```

**Redacción de PII:**
- User queries: hash SHA256 en logs, contenido original solo en debug mode
- Profile IDs: loguear (no son PII)
- Prompt completo: NO loguear en producción (contiene query del usuario)

---

### Frontend

#### Nuevos componentes

Ninguno nuevo necesario. Los componentes existentes cubren la funcionalidad:
- `ProfileManager` (profiles.js): gestión de perfiles
- `CardRenderer` (cards.js): renderizado de tourism_data
- `ChatHandler` (chat.js): envío de mensajes con user_preferences

#### Patrones aplicados

- **Observer** (implícito): `ProfileManager.setActiveProfile()` → `updateBadge()` → UI actualizada
- **Factory**: `CardRenderer.render(tourismData)` decide qué cards generar según datos disponibles

#### Separación de responsabilidades

| Concern | Ubicación actual | Correcto? |
|---------|-----------------|-----------|
| UI render | `profiles.js` (modal), `cards.js`, `chat.js` | ✅ |
| State management | `ProfileManager` (LocalStorage) | ✅ |
| API communication | `chat.js` (fetch) | ✅ |
| Business logic | Ninguna en frontend | ✅ Correcto — sin lógica de negocio en UI |

#### Fallbacks frontend

| Escenario | Comportamiento actual | Adecuado? |
|-----------|---------------------|-----------|
| `profiles.json` no carga | Lista vacía + warning console | ✅ |
| `active_profile_id` no en registry | Clear LocalStorage + null | ✅ |
| LocalStorage no disponible | Fallback a memoria de sesión | ✅ |
| `tourism_data = null` | No renderiza cards (solo texto) | ⚠️ Degradación aceptable pero pierde valor |
| Backend error (502/503) | Alert de error | ✅ |

---

### Integración

#### Punto exacto de conexión

```
Frontend chat.js:sendMessage()
  → POST /api/v1/chat/message
    → chat.py:send_message() [línea 31]
      → backend_adapter.py:process_query() [línea 60]
        → profile_service.py:resolve_profile() [línea 61]
        → agent.py via orchestrator.py:process_request() [línea 86]
          → agent.py:_execute_pipeline() [línea 54]
          → response_prompt.py:build_response_prompt() [línea 53]
          → llm.invoke() [línea 53 de orchestrator.py]
          → agent.py:_extract_structured_data() [línea 181]
```

#### Activación de feature

**Actual:** Profile siempre activo si `active_profile_id` está presente en request.

**Propuesto:** Feature flags en `Settings`:
```python
use_profile_ranking = Field(default=False)  # Controla si ranking_bias se aplica
```

Detección: `settings.use_profile_ranking and profile_context is not None`

#### Desacoplamiento

**Actual:** Fuerte acoplamiento entre capas (ver sección d).

**Propuesto:**
1. Interfaces estables en Shared para cada boundary
2. Factory pattern para instanciación de componentes
3. `API_REFERENCE.md` como contrato versionado entre frontend y backend

---

## 4.4 Reglas de Diseño — Evaluación de Cumplimiento

| Regla | Cumplimiento actual | Violaciones detectadas | Corrección propuesta |
|-------|--------------------|-----------------------|---------------------|
| Separación por capas | ⚠️ Parcial | `dependencies.py` (Shared→Application), `canonicalizer.py` (Business→Application), `ProfileService` (Application→Presentation file) | Mover DI a Application, mover models compartidos a Shared, inyectar profile path via Settings |
| No lógica de negocio en UI | ✅ Cumple | Ninguna | — |
| No acoplar UI a contratos internos | ✅ Cumple | Frontend solo usa REST API contract | — |
| Open/Closed | ⚠️ Parcial | `_execute_pipeline()` hardcoded para 4 tools, no extensible | Configurar pipeline via lista de tools inyectada |
| Validación defensiva en boundaries | ⚠️ Parcial | `message` sin max_length, `profile_id` sin validación de formato | Añadir Field validators en Pydantic models |
| No duplicar lógica | ⚠️ Parcial | Schema JSON duplicado entre `response_prompt.py:3-21` y `TourismData` Pydantic model | Generar schema string desde Pydantic model |
| No dependencias innecesarias | ✅ Cumple | — | — |
| Dependencias apuntan hacia adentro | ❌ Viola | `shared/utils/dependencies.py` apunta hacia Application (hacia fuera) | Mover a `application/di/` o `presentation/di/` |
| Interfaces en capas internas | ⚠️ Parcial | `ProfileService` y `MultiAgentOrchestrator` no tienen interfaces en Shared | Crear `ProfileResolverInterface` y ya existe `MultiAgentInterface` ✅ |
| Side-effects aislados en Integration | ✅ Cumple | STT services, settings — todo en Integration | — |

---

## 4.5 Validación Defensiva

### Tabla de escenarios

| Escenario | Comportamiento esperado | Error/Respuesta | Logging | Métrica |
|-----------|------------------------|----------------|---------|---------|
| `active_profile_id = null` | Comportamiento default (sin ranking) | 200 OK, respuesta normal | `profile_id=none` | `profile_null_count++` |
| `active_profile_id = "unknown_id"` | Tratar como null + warning | 200 OK, sin ranking | `WARN: Unknown profile_id` | `profile_unknown_count++` |
| `profiles.json` no encontrado | ProfileService retorna {} + error log | 200 OK, sin ranking, sin crash | `ERROR: Profile registry not found` | `registry_load_error_count++` |
| `profiles.json` JSON inválido | ProfileService retorna {} + error log | 200 OK, sin ranking | `ERROR: Profile registry invalid JSON` | `registry_parse_error_count++` |
| LLM no emite JSON block | Usar tool_data como tourism_data | 200 OK, datos de tools (o null) | `WARN: LLM returned no JSON block` | `llm_json_miss_count++` |
| LLM emite JSON inválido | Retry con tool_data, fallback null | 200 OK, datos parciales | `WARN: LLM JSON parse failed` | `llm_json_invalid_count++` |
| OpenAI API timeout (>30s) | Retry x2, luego error | 502 Backend error | `ERROR: LLM timeout after 30s` | `llm_timeout_count++` |
| OpenAI API rate limit (429) | Retry con backoff, luego error | 502 Backend error | `ERROR: OpenAI rate limit` | `llm_rate_limit_count++` |
| Google Maps API falla (Fase 4) | Fallback a cached data o mock data | 200 OK, datos cached | `WARN: Google Maps API failed, using cache` | `api_fallback_count++` |
| `tourism_data` parcialmente válido | Aceptar campos válidos, null para inválidos | 200 OK, cards parciales | `INFO: Partial canonicalization` | `partial_data_count++` |
| Frontend LocalStorage inaccesible | ProfileManager usa memoria de sesión | Sin persistencia entre recargas | Console warn | N/A (frontend) |
| `message` vacío o solo whitespace | 400 Bad Request | HTTPException 400 | `WARN: Empty message rejected` | `validation_error_count++` |

### Políticas de retry/timeout

| Componente | Timeout | Max retries | Backoff | Fallback |
|-----------|---------|-------------|---------|----------|
| LLM (GPT-4) | 30s | 2 | Exponencial (1s, 2s) | Error 502 |
| Google Maps API | 10s | 1 | Ninguno | Datos cached o mock |
| Canonicalization | N/A | 2 | Ninguno | tool_data → llm_data → null |
| Profile resolution | N/A | 0 | N/A | null (sin perfil) |

---

## 5. Requisitos LLM/Agentes

### 5.1 Separación de concerns LLM

| Concern | Estado actual | Ubicación | Estado deseado |
|---------|--------------|-----------|----------------|
| **Prompt engineering** | Parcialmente separado | `response_prompt.py`, `system_prompt.py` | ✅ Mantener separado, añadir versionado |
| **Orquestación** | Template Method en orchestrator.py | `business/core/orchestrator.py` | ✅ Mantener, extender para profile-aware pipeline |
| **Validación estructural** | Regex-based en agent.py | `agent.py:181-221` | ❌ Migrar a structured output / function calling |

### 5.2 Validación post-LLM contra SSOT

**SSOT:** `TourismData` Pydantic model (actualmente en `application/models/responses.py`, propuesto mover a `shared/models/tourism.py`).

**Flujo de validación propuesto:**
```
LLM output
  → Parse (structured output o regex fallback)
  → Validate contra TourismData schema (Pydantic)
  → Canonicalize (normalize facilities, levels, scores)
  → Si válido: usar
  → Si inválido: retry una vez con prompt mejorado
  → Si sigue inválido: usar tool_data como fallback
  → Si tool_data también inválido: tourism_data = null + log error
```

### 5.3 Protección contra respuestas no estructuradas

**Actual:** Si LLM no emite `\`\`\`json...\`\`\``, `tourism_data = null`. Sin retry.

**Propuesto (Fase 2):**
1. Usar `response_format={"type": "json_object"}` de OpenAI para forzar JSON
2. O usar LangChain `llm.with_structured_output(TourismData)` para validación automática
3. Fallback chain: structured output → regex parse → tool data → null

### 5.4 Logging de respuestas LLM

```python
# Log redactado por request:
logger.info(
    "llm_response_processed",
    correlation_id=correlation_id,
    prompt_hash=sha256(prompt),  # NO el contenido
    response_length=len(response_text),
    tokens_input=usage.prompt_tokens,
    tokens_output=usage.completion_tokens,
    json_extracted=True/False,
    json_valid=True/False,
    canonicalization_success=True/False,
    profile_directives_count=len(directives),
)
```

### 5.5 Tolerancia a outputs parcialmente válidos

**Ejemplo:** LLM devuelve JSON con `venue` válido pero `routes` inválido.

**Comportamiento:** Aceptar `venue`, poner `routes = null`, log warning con detalles del campo inválido. Frontend (`CardRenderer`) ya maneja ausencia de cada sección independientemente.

### 5.6 Versionado de prompts

**Propuesta:** Añadir constante `PROMPT_VERSION` en cada archivo de prompt:

```python
# response_prompt.py
PROMPT_VERSION = "1.1.0"

# system_prompt.py
PROMPT_VERSION = "1.0.0"
```

Log del `prompt_version` en cada invocación para correlacionar cambios de prompt con cambios de calidad.

### 5.7 Golden outputs

Crear `tests/fixtures/golden_outputs/` con:
- Input query
- Profile ID
- Expected tourism_data structure (no texto exacto, sino schema compliance + venue type match)

Ejemplo:
```json
{
  "query": "Recomiéndame actividades en Madrid esta noche",
  "profile_id": "night_leisure",
  "expected": {
    "venue_type_in": ["entertainment", "nightclub", "restaurant"],
    "tourism_data_not_null": true,
    "text_contains_any": ["noche", "nocturno", "concierto", "bar"]
  }
}
```

### 5.8 Límites de tokens/coste

| Parámetro | Valor actual | Valor propuesto | Degradación |
|-----------|-------------|----------------|-------------|
| `max_tokens` (response) | 2500 | 2000 (reducir coste) | Respuestas más concisas |
| `temperature` | 0.3 | 0.3 ✅ | — |
| Coste estimado/request | ~$0.15 (GPT-4) | ~$0.15 (single call) o ~$0.30 (dual call) | Considerar GPT-4-turbo ($0.03/request) |
| Presupuesto diario | No definido | $10/día (POC), $50/día (producción) | Rate limiting si se excede |
| Fallback si presupuesto agotado | No existe | Modo simulación automático | Respuestas simuladas (existentes) |

---

## 4.7 Definition of Done (Checklist Verificable)

### Checklist General

- [ ] ✅ No rompe funcionalidades existentes — tests de regresión pasan
- [ ] ✅ No viola separación por capas — audit de imports
- [ ] ✅ No introduce dependencias innecesarias — review de pyproject.toml
- [ ] ✅ Maneja errores correctamente — todos los paths de error tienen handler
- [ ] ✅ Es extensible — nuevo perfil = solo agregar a profiles.json
- [ ] ✅ Es testeable — todos los servicios inyectables via interfaces

### Checklist Específico por Fase

**Fase 0:**
- [ ] `API_REFERENCE.md` refleja contrato real
- [ ] ≥15 tests unitarios/integración
- [ ] Feature flags en Settings
- [ ] Violación de capas `dependencies.py` corregida
- [ ] Correlation ID en logs

**Fase 1:**
- [ ] `tourism_data_null_rate < 20%`
- [ ] LLM timeout + retry configurado
- [ ] Token tracking en logs
- [ ] PII redactado en logs

**Fase 2:**
- [ ] `tourism_data_null_rate < 5%`
- [ ] Structured output como path principal
- [ ] Regex solo como fallback
- [ ] Latencia p95 < 15s

**Fase 3:**
- [ ] Profile ranking aplicado
- [ ] Test: perfiles diferentes → orden diferente
- [ ] `profile_venue_type_match_rate > 70%`
- [ ] Métricas de profile impact en logs

**Fase 4:**
- [ ] Tools con APIs reales
- [ ] Funciona para ≥5 ciudades
- [ ] Fallback a cache cuando API falla
- [ ] Anti-corruption layer implementado

**Fase 5:**
- [ ] Rate limiting activo
- [ ] Auth implementado
- [ ] Conversaciones persistidas
- [ ] CORS restringido
- [ ] Cobertura tests ≥ 70%
- [ ] Archivos huérfanos eliminados

### Contract Tests (alineados con API_REFERENCE.md)

- [ ] `POST /chat/message` acepta `user_preferences.active_profile_id`
- [ ] Response incluye `tourism_data` con schema `TourismData` cuando hay datos
- [ ] Response incluye `pipeline_steps` con schema `PipelineStep[]`
- [ ] `profile_id` inválido → respuesta 200 (sin ranking, no error)
- [ ] `user_preferences` ausente → respuesta 200 (comportamiento default)

### Métricas mínimas en producción

| Métrica | Target | Cómo medir |
|---------|--------|-----------|
| Latencia p50 | < 5s | structlog + aggregation |
| Latencia p95 | < 15s | structlog + aggregation |
| Error rate | < 2% | HTTP status codes 5xx / total |
| `tourism_data` valid rate | > 95% | `tourism_data != null` / total |
| Profile match rate | > 70% | `venue_type in expected_types` / profiled requests |
| Coste LLM diario | < $50 | Token tracking + OpenAI billing |
| Parse success rate | > 95% | `json_valid` / `json_attempted` |

### Rollback plan

Cada fase controlada por feature flag. Rollback = desactivar flag en `.env`:

```bash
# Rollback Fase 3
VOICEFLOW_USE_PROFILE_RANKING=false

# Rollback Fase 2
VOICEFLOW_USE_FUNCTION_CALLING=false

# Rollback Fase 4
VOICEFLOW_USE_REAL_TOOLS=false
```

Test de rollback: desactivar cada flag → sistema funciona como antes del refactor.

---

## 6. Resumen de Inconsistencias y Correcciones

### Inconsistencias documentación ↔ código

| # | Inconsistencia | Doc → Corrección |
|---|---------------|-----------------|
| I1 | `API_REFERENCE.md` no documenta `user_preferences` en ChatRequest | Actualizar `API_REFERENCE.md` sección Chat con campo `user_preferences` |
| I2 | `API_REFERENCE.md` no documenta `tourism_data`, `pipeline_steps`, `intent`, `entities` en ChatResponse | Actualizar `API_REFERENCE.md` con schema completo de ChatResponse |
| I3 | `API_REFERENCE.md` `BackendInterface.process_query()` sin `active_profile_id` | Actualizar firma en doc para incluir `active_profile_id: Optional[str]` |
| I4 | `API_REFERENCE.md` ConversationInterface implementada por `integration/...` | Corregir a `application/services/conversation_service.py` |
| I5 | `ESTADO_ACTUAL_SISTEMA.md` referencia `get_profile_by_id()` | Corregir a `resolve_profile()` |
| I6 | `REFACTOR_PLAN` referencia `get_profile_context()` inexistente | Corregir a `resolve_profile()` y ajustar propuesta de enriquecimiento |

### Incompatibilidades refactor ↔ arquitectura actual

| # | Incompatibilidad | Propuesta de ajuste |
|---|-----------------|-------------------|
| IC1 | REFACTOR_PLAN propone añadir `profile_context` a `BaseTool._run()` signature, pero LangChain `_run()` acepta solo `(self, input: str)` | **Alternativa:** Usar state injection via constructor o class-level attribute. Cada tool recibe `profile_context` en `__init__()` o como `tool.context = profile_context` antes de ejecutar pipeline. O migrar a `DomainToolInterface` propia. |
| IC2 | REFACTOR_PLAN propone `functions=` y `function_call=` (deprecated OpenAI syntax) | **Corrección:** Usar `tools=` y `tool_choice=` (nueva API) o LangChain `with_structured_output()` |
| IC3 | REFACTOR_PLAN propone 2 LLM invocations (texto + JSON) duplicando coste | **Alternativa:** Single call con `response_format={"type": "json_object"}` para el JSON, o single call con `with_structured_output()` que retorna Pydantic object directamente |
| IC4 | REFACTOR_PLAN pone derivación de `expected_types` en `ProfileService` (Application) | **Corrección:** Esto es lógica de negocio. Mover a `ProfileRankingPolicy` en Business layer |
| IC5 | REFACTOR_PLAN propone `_apply_profile_ranking()` que modifica `accessibility_score` in-place | **Corrección:** No mutar accessibility_score real (es un dato objetivo). Ranking debe usar score separado (`relevance_score = base_score * bias`) |

### Errores de arquitectura/diseño

| # | Error | Corrección propuesta |
|---|-------|---------------------|
| E1 | `shared/utils/dependencies.py` importa clases concretas de Application (viola Clean Architecture) | Mover DI functions a `application/di/providers.py` o `presentation/di/`. Shared solo define interfaces. |
| E2 | `business/core/canonicalizer.py` importa `TourismData` de Application models (Business→Application) | Mover `TourismData` y related models a `shared/models/tourism.py` |
| E3 | `ProfileService` accede a filesystem de Presentation (`presentation/static/config/profiles.json`) | Inyectar path via `Settings` o servir profiles via endpoint REST |
| E4 | `TourismMultiAgent` instanciado directamente en `backend_adapter.py` sin factory/DI | Usar factory o lazy initialization con interfaz `MultiAgentInterface` |
| E5 | `conversation_history` es estado mutable de instancia en `MultiAgentOrchestrator` | Persistir en storage externo (Redis/SQLite). No mantener state en service instance. |
| E6 | Archivos huérfanos en root: `langchain_agents.py`, `azure_test.py`, `azure_test2.py`, `test_voiceflow.py` | Eliminar o mover a ubicación correcta (tests/ o integration/) |
| E7 | Schema JSON duplicado: `response_prompt.py:TOURISM_DATA_SCHEMA` vs `TourismData` Pydantic model | Generar schema string desde `TourismData.schema_json()` |

---

**Fuente de verdad post-refactor:**
- **Contratos API:** `API_REFERENCE.md` (actualizado)
- **Schemas/DTOs:** `shared/models/tourism.py` (nuevo, Pydantic models)
- **Profile registry:** `presentation/static/config/profiles.json`
- **Prompt templates:** `business/domains/tourism/prompts/` (versionados)
- **Feature flags:** `integration/configuration/settings.py`
