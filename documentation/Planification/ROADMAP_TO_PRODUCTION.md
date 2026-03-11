# Roadmap: POC → Production

**Fecha:** 11 de Marzo de 2026
**Branch base:** `feature/real-tools-implementation`
**Contexto:** Basado en [AUDIT_2026_03_11.md](../Reviews/AUDIT_2026_03_11.md)

---

## 1. Resumen Ejecutivo

### Estado actual del POC

El sistema es un asistente de turismo accesible con arquitectura en 4 capas, pipeline multi-agente (NLU + NER + 3 domain tools), integración con APIs reales (Google Places, Google Routes, OpenRouteService, Overpass/OSM) y fallback automático a datos mock. Cuenta con 156 test functions, contratos tipados Pydantic, y capa de resiliencia (circuit breaker + rate limiter + budget tracker).

### Principales gaps para llegar a producción

| Gap | Impacto | Referencia auditoría |
|-----|---------|---------------------|
| Zero autenticación/autorización | Cualquier actor puede consumir la API y generar costes en OpenAI/Google | TD-11, B4 |
| Persistencia en memoria | Se pierde todo estado en cada restart; sin concurrencia segura | TD-09 |
| Sin CI/CD | No hay validación automática pre-merge; deploys manuales | — |
| Sin observabilidad operativa | Logs existen pero no hay métricas, alertas ni dashboards | — |
| Pipeline fijo (fan-out total) | Toda query ejecuta todos los tools — coste y latencia innecesarios | TD-07 |
| Profile no afecta ranking | El perfil cambia el tono del texto pero no los venues recomendados | TD-PROFILE-01..04 |
| CORS `*` en producción | Permite requests desde cualquier origen | TD-11 |
| `console.log` en frontend (76 ocurrencias) | Debug noise en browser del usuario final | TD-08 |

### Estrategia general de evolución

```
Fase 0: Hardening (cerrar gaps de seguridad y estabilidad mínima)
   ↓
Fase 1: MVP Producción (persistencia, CI/CD, observabilidad básica)
   ↓
Fase 2: Inteligencia (routing por intent, profile ranking, query optimization)
   ↓
Fase 3: Escala (multi-tenant, CDN, caching distribuido, i18n)
```

La Fase 0 es bloqueante: sin ella, exponer el sistema a usuarios reales implica riesgo financiero (OpenAI/Google sin control) y de datos (sin auth).

---

## 2. Principios de diseño para la versión de producción

### Escalabilidad
- Stateless application servers; estado en PostgreSQL + Redis
- Servicios externos detrás de la capa de resiliencia existente (circuit breaker + rate limiter + budget tracker)
- Pipeline selectivo por intent para reducir llamadas API

### Observabilidad
- Structured logging ya implementado (structlog) — extender con correlation IDs
- Métricas Prometheus en cada tool del pipeline (latencia, error rate, fallback rate)
- Health checks ya presentes — extender con readiness/liveness para Kubernetes

### Seguridad
- API keys como primer paso (PoC scope); JWT si se necesita multi-tenant
- Rate limiting público por IP/API key (el rate limiter actual es para APIs externas salientes, no para tráfico entrante)
- HTTPS obligatorio; CORS restrictivo por dominio
- Input sanitization en NLU (prompt injection mitigation)

### Mantenibilidad
- El sistema ya tiene interfaces ABC + factories + DI — mantener este patrón
- Mover DI composition root de `shared/` a `application/` (TD-01)
- Extraer simulación (~110 líneas hardcodeadas) del adapter a un mock service separado (TD-04)

### Experiencia de usuario
- Latencia percibida: streaming de respuesta LLM (actualmente es request-response completo)
- Feedback visual del pipeline (ya existe `pipeline_steps` en API response — frontend lo consume)
- Geolocalización del usuario para búsquedas relevantes (componente implementado en branch)

---

## 3. Roadmap por fases

### Fase 0: Hardening del POC

**Objetivo:** Cerrar los gaps que hacen imposible exponer el sistema a usuarios externos.

**Problemas que resuelve:**
- API completamente abierta (cualquier actor puede generar costes)
- CORS permisivo
- Sin HTTPS
- Frontend con debug logging
- Simulation code acoplado al adapter

**Entregables:**
1. Autenticación por API key en todos los endpoints
2. Rate limiting por IP/key en tráfico entrante
3. HTTPS (TLS termination)
4. CORS restrictivo por dominio configurado
5. Limpieza frontend: `console.log` → logger configurable
6. Extraer simulación del backend adapter a servicio separado
7. Mover DI root de `shared/utils/dependencies.py` a `application/`

---

### Fase 1: MVP Producción

**Objetivo:** Sistema desplegable y operable con persistencia real, CI/CD, y observabilidad mínima.

**Problemas que resuelve:**
- Estado perdido en cada restart
- Sin validación automática de código
- Sin métricas operativas
- Deploy manual

**Entregables:**
1. Persistencia en PostgreSQL (conversaciones, sesiones)
2. Redis para cache (geocoding, NLU results, session state)
3. CI/CD pipeline (GitHub Actions: lint, test, build, deploy staging)
4. Métricas Prometheus + dashboard Grafana básico
5. Correlation IDs en toda la cadena de request
6. Health checks extendidos (readiness/liveness)
7. Docker production hardening (non-root user, multi-stage build, secrets injection)

---

### Fase 2: Inteligencia

**Objetivo:** El sistema da respuestas relevantes por contexto, reduce costes API, y el perfil del usuario tiene impacto real.

**Problemas que resuelve:**
- Pipeline fijo ejecuta todos los tools siempre (coste innecesario)
- Perfil solo afecta tono, no venues
- Búsquedas duplicadas o de baja señal ("Almería Almería")
- Sin geolocalización del usuario en búsquedas

**Entregables:**
1. Routing por intent (NLU intent → subset de tools a ejecutar)
2. Profile-driven ranking de venues
3. Query builder canónico (deduplicación, normalización)
4. User location integration en PlacesSearchTool
5. Streaming de respuesta LLM (SSE/WebSocket)

---

### Fase 3: Escala y expansión

**Objetivo:** Sistema multi-tenant, multi-idioma, con caching distribuido y capacidad de crecimiento.

**Problemas que resuelve:**
- Single-tenant
- Solo español
- Sin CDN para assets
- Cache local solamente

**Entregables:**
1. Multi-tenant con JWT + tenant isolation
2. i18n (inglés como segundo idioma: NLU, NER, prompts, UI)
3. CDN para static assets
4. Caching distribuido (Redis cluster)
5. Evaluación de LangGraph como runtime de orquestación

---

## 4. Features por fase

### FASE 0

#### F0.1 — API Key Authentication

Proteger todos los endpoints REST con autenticación por API key.

**Valor:** Impide que actores no autorizados generen costes en OpenAI/Google y accedan a datos de conversaciones.

**User Stories:**
- As a system operator, I want to restrict API access to authorized clients, so that I control who can generate costs against external APIs.
- As a developer integrating with the API, I want to authenticate with an API key in the `Authorization` header, so that I have a simple and standard auth mechanism.

**Acceptance Criteria:**
- Requests sin API key válida reciben `401 Unauthorized`
- API keys almacenadas con hash (bcrypt/argon2), nunca en plaintext
- Endpoint `GET /api/v1/health/` permanece público (sin auth)
- API key se pasa via header `Authorization: Bearer <key>` o `X-API-Key: <key>`
- Existe comando CLI o endpoint admin para generar/revocar keys

**Notas técnicas:**
- `AuthInterface` ya está definida en `shared/interfaces/interfaces.py` (actualmente sin implementación)
- `auth_enabled` y `auth_provider` ya existen en `Settings`
- Middleware de FastAPI para validación antes de routing

---

#### F0.2 — Inbound Rate Limiting

Rate limiter para tráfico entrante (distinto al rate limiter de APIs externas salientes que ya existe).

**Valor:** Previene abuso, DoS, y consumo descontrolado de recursos.

**User Stories:**
- As a system operator, I want to limit requests per client, so that a single client cannot exhaust system resources or API budgets.

**Acceptance Criteria:**
- Límite configurable por API key (default: 30 req/min para `/chat/message`, 60 req/min para otros)
- Respuesta `429 Too Many Requests` con header `Retry-After`
- Límite global por IP para requests no autenticados (10 req/min)
- Configuración via env vars: `VOICEFLOW_PUBLIC_RATE_LIMIT_RPM`, `VOICEFLOW_CHAT_RATE_LIMIT_RPM`

**Notas técnicas:**
- Usar `slowapi` o middleware custom con token bucket (similar al `TokenBucketRateLimiter` existente en `resilience.py`)
- En Fase 1, migrar a Redis-backed rate limiter para compatibilidad multi-instancia

---

#### F0.3 — HTTPS + CORS Hardening

**Valor:** Previene MITM attacks y restringe qué orígenes pueden consumir la API.

**User Stories:**
- As a user, I want my data encrypted in transit, so that my conversations are private.
- As a system operator, I want to restrict CORS origins, so that only authorized frontends access the API.

**Acceptance Criteria:**
- TLS termination configurada (certbot/Let's Encrypt o cloud load balancer)
- `cors_origins` en producción contiene solo dominios autorizados (no `*`)
- HTTP requests redirigen a HTTPS
- `Strict-Transport-Security` header presente

**Notas técnicas:**
- `get_cors_config()` en `settings.py:200` ya distingue production vs development
- Solo necesita configurar `cors_origins` correctamente y forzar `is_production()` en deploy

---

#### F0.4 — Frontend Logging Cleanup

**Valor:** Elimina debug noise en browser del usuario final; permite diagnóstico controlado.

**User Stories:**
- As a user, I want a clean browser console, so that I don't see internal debug messages.
- As a developer, I want configurable frontend logging levels, so that I can enable verbose logging only when debugging.

**Acceptance Criteria:**
- 0 `console.log` directos en producción (todos pasan por logger wrapper)
- Logger configurable con niveles: `debug`, `info`, `warn`, `error`
- Nivel default en producción: `warn`
- Nivel en desarrollo: `debug`

**Notas técnicas:**
- 76 `console.log` en 7 archivos JS bajo `presentation/static/js/`
- Crear `presentation/static/js/logger.js` con wrapper y nivel configurable via `window.VOICEFLOW_LOG_LEVEL`

---

#### F0.5 — Extract Simulation to Mock Service

**Valor:** SRP: el adapter orquesta; el mock simula. Simplifica testing y mantenimiento.

**User Stories:**
- As a developer, I want simulation logic separated from production adapter, so that I can maintain and test each independently.

**Acceptance Criteria:**
- `LocalBackendAdapter._simulate_ai_response()` eliminado del adapter
- Nueva clase `SimulatedBackendService` implementando `BackendInterface`
- DI selecciona implementación según `use_real_agents` setting
- Tests de simulación existentes pasan sin cambios

**Notas técnicas:**
- ~110 líneas de respuestas hardcodeadas en `backend_adapter.py`
- `SimulatedBackendService` en `application/orchestration/` o `integration/`

---

#### F0.6 — DI Composition Root Relocation

**Valor:** Corrige violación de capas arquitectónicas (shared no debe depender de application).

**User Stories:**
- As a developer, I want DI wiring in the application layer, so that layer dependencies flow correctly downward.

**Acceptance Criteria:**
- `dependencies.py` movido de `shared/utils/` a `application/di/`
- Imports actualizados en todos los consumers (API endpoints)
- `shared/` no importa nada de `application/` ni `integration/`
- Tests pasan

**Notas técnicas:**
- Actualmente `shared/utils/dependencies.py` importa `application.orchestration.backend_adapter` y `application.services.*` — esto invierte la dependencia de capas

---

### FASE 1

#### F1.1 — PostgreSQL Persistence

**Valor:** Conversaciones persisten entre restarts; base para analytics y auditoría.

**User Stories:**
- As a user, I want my conversation history to persist, so that I can return to previous interactions.
- As a system operator, I want conversation data in a database, so that I can run analytics and audits.

**Acceptance Criteria:**
- `ConversationService` respaldado por PostgreSQL (SQLAlchemy async + Alembic migrations)
- Schema: `conversations`, `messages`, `api_keys` (para F0.1)
- Migración automática en startup
- Fallback a in-memory si DB no disponible (degraded mode)
- Connection pooling configurado

**Notas técnicas:**
- `ConversationInterface` ya definida — solo cambiar implementación
- `database_enabled` y `database_url` ya existen en Settings
- `integration/data_persistence/conversation_repository.py` es el punto de cambio

---

#### F1.2 — Redis Cache Layer

**Valor:** Reduce latencia y costes de APIs externas; prerequisito para rate limiting distribuido.

**User Stories:**
- As a system operator, I want API responses cached, so that repeated queries don't generate redundant external API calls.

**Acceptance Criteria:**
- Geocoding cache en Redis (actualmente in-memory con TTL en `CachedGeocodingService`)
- NLU results cache (misma query → mismo intent, skip OpenAI call)
- Session state en Redis (para multi-instance)
- TTL configurable por tipo de cache
- Fallback a in-memory cache si Redis no disponible

**Notas técnicas:**
- `CachedGeocodingService` ya tiene lógica de cache — extraer a abstracción `CacheInterface`
- `geocoding_cache_ttl` (1h) y `google_places_cache_ttl` (24h) ya definidos en Settings

---

#### F1.3 — CI/CD Pipeline

**Valor:** Validación automática pre-merge; deploy reproducible.

**User Stories:**
- As a developer, I want automated checks on every PR, so that broken code doesn't reach main.
- As a system operator, I want automated deployments, so that releases are reproducible and auditable.

**Acceptance Criteria:**
- GitHub Actions workflow: `ruff check` → `ruff format --check` → `pytest` → Docker build
- PR blocked if any step fails
- Staging deploy automático en merge a `main`
- Production deploy manual con approval gate
- Coverage report en PR comments

**Notas técnicas:**
- `pyproject.toml` ya configura ruff, pytest markers, y coverage threshold (70%)
- Docker files ya existen: `Dockerfile`, `docker-compose.prod.yml`
- `.github/` directory exists (needs workflow files)

---

#### F1.4 — Prometheus Metrics + Grafana Dashboard

**Valor:** Visibilidad operativa: latencia, error rate, costes API, health.

**User Stories:**
- As a system operator, I want a dashboard showing system health and API costs, so that I can detect issues before users report them.

**Acceptance Criteria:**
- Métricas expuestas en `/metrics` (Prometheus format)
- Métricas por tool: `tool_duration_seconds`, `tool_error_total`, `tool_fallback_total`
- Métricas por API externa: `external_api_cost_usd`, `circuit_breaker_state`
- Métricas de negocio: `chat_requests_total`, `nlu_intent_distribution`, `profile_usage`
- Dashboard Grafana con paneles: latencia p50/p95, error rate, cost/hour, active circuits

**Notas técnicas:**
- `BudgetTracker` en `resilience.py` ya calcula costes — exponer como métrica
- `pipeline_steps` ya tiene `duration_ms` por tool — instrumentar con Prometheus histograms
- Usar `prometheus-fastapi-instrumentator` para métricas HTTP automáticas

---

#### F1.5 — Correlation IDs

**Valor:** Trazar una request completa desde API entry hasta respuesta LLM para debugging.

**User Stories:**
- As a developer debugging an issue, I want a single ID that links all logs for one request, so that I can trace the full execution path.

**Acceptance Criteria:**
- Middleware genera `X-Request-ID` UUID si no viene en request
- ID propagado a todos los logs (structlog context)
- ID incluido en response header `X-Request-ID`
- ID presente en `metadata` del `ChatResponse`

**Notas técnicas:**
- structlog ya está configurado globalmente — usar `structlog.contextvars` para propagación automática

---

### FASE 2

#### F2.1 — Intent-Based Tool Routing

**Valor:** Reduce latencia 40-60% y coste API proporcional al eliminar tool calls irrelevantes.

**User Stories:**
- As a user, I want faster responses, so that the conversation feels natural.
- As a system operator, I want to minimize unnecessary API calls, so that I reduce operating costs.

**Acceptance Criteria:**
- Mapping `intent → tools[]` configurable (e.g., `venue_search` → [Places, Accessibility]; `route_planning` → [Places, Directions])
- `general_query` ejecuta solo NLU+NER (sin domain tools)
- Fallback: si intent desconocido, fan-out completo (comportamiento actual)
- Métricas: `tools_skipped_total` por intent
- Latencia p50 de `/chat/message` reduce ≥30% en queries no-routing

**Notas técnicas:**
- El intent ya está disponible post-NLU en `nlu_result.intent`
- Modificar `_execute_pipeline_async()` en `agent.py` para routing condicional
- Ver `PLAN_FASES_PLACESSEARCHTOOL_PRODUCCION.md` Phase 1 (IntentSearchPolicy) como referencia

---

#### F2.2 — Profile-Driven Venue Ranking

**Valor:** Las recomendaciones se adaptan al perfil del usuario — el sistema deja de contradecirse.

**User Stories:**
- As a user with "night_leisure" profile, I want nightlife recommendations prioritized, so that the results match my interests.
- As a user with "cultural" profile, I want museums and exhibitions first, so that I discover cultural activities.

**Acceptance Criteria:**
- `PlacesSearchTool` ajusta query y tipo según `profile_context.expected_types`
- Resultados rankeados por relevancia al perfil (no solo proximidad/rating)
- Test: misma query con perfil `night_leisure` vs `cultural` devuelve diferentes top-3 venues
- `profile_context.ranking_bias` efectivamente consumido (actualmente ignorado)

**Notas técnicas:**
- `ToolPipelineContext` ya transporta `profile_context` a todos los tools
- `DirectionsTool` ya consume `accessibility_needs` — extender patrón a `PlacesSearchTool`
- Ver `REFACTOR_PLAN_PROFILE_DRIVEN_RESPONSES.md` Phases 3-4

---

#### F2.3 — Query Builder + Deduplication

**Valor:** Mejora relevancia de búsquedas Google Places; reduce queries duplicadas/vacías.

**User Stories:**
- As a user, I want accurate place search results, so that I don't get irrelevant recommendations.

**Acceptance Criteria:**
- Queries normalizadas: trim, dedup ("Almería Almería" → "Almería"), case normalization
- `resolved_entities.destination` priorizado sobre free text
- Logging: `query_original` vs `query_final` para auditoría
- Top-1 relevance mejora ≥20% en evaluation dataset

**Notas técnicas:**
- Ver `PLAN_FASES_PLACESSEARCHTOOL_PRODUCCION.md` Phase 2

---

#### F2.4 — User Location in Search

**Valor:** Búsquedas cerca del usuario en lugar de genéricas por ciudad.

**User Stories:**
- As a user who shared my location, I want nearby results, so that I get recommendations I can actually walk to.

**Acceptance Criteria:**
- Frontend envía coordenadas GPS (con consentimiento) en `user_preferences.location`
- `PlacesSearchTool` usa coordenadas como centro de búsqueda
- `DirectionsTool` usa coordenadas como punto de partida
- Sin location: comportamiento actual (búsqueda por nombre de ciudad)

**Notas técnicas:**
- Componente de geolocalización ya implementado en branch (`SPECS_USER_LOCATION.md`)
- `GeocodedLocation` model ya existe en `tool_models.py`

---

#### F2.5 — LLM Response Streaming

**Valor:** El usuario ve la respuesta construirse en tiempo real — reduce latencia percibida.

**User Stories:**
- As a user, I want to see the response appear progressively, so that I don't stare at a loading spinner for 3-5 seconds.

**Acceptance Criteria:**
- Endpoint streaming via SSE (`text/event-stream`)
- Tokens del LLM enviados incrementalmente
- `tourism_data` y `pipeline_steps` enviados como evento final
- Frontend renderiza texto progresivamente
- Endpoint sync existente (`/chat/message`) se mantiene como fallback

**Notas técnicas:**
- LangChain `ChatOpenAI` soporta streaming nativo
- `audio.py` ya tiene `stream-config` endpoint placeholder
- Frontend `chat.js` necesita EventSource handler

---

### FASE 3

#### F3.1 — Multi-Tenant with JWT

**Valor:** Múltiples organizaciones pueden usar el sistema con aislamiento de datos.

**User Stories:**
- As a platform operator, I want multiple tenants, so that each client has isolated data and configuration.

**Acceptance Criteria:**
- JWT con `tenant_id` claim
- Queries filtradas por tenant en PostgreSQL
- Budget tracker per-tenant
- API keys scoped por tenant

---

#### F3.2 — Internationalization (i18n)

**Valor:** Expandir mercado más allá de hispanohablantes.

**User Stories:**
- As an English-speaking tourist, I want to interact in English, so that I can use the system in my language.

**Acceptance Criteria:**
- NLU funciona en inglés (`ner_model_map` ya soporta `en: en_core_web_sm`)
- Prompts del LLM adaptados por idioma
- UI traducida (labels, placeholders, demo scenarios)
- Detección automática de idioma o selector manual

---

#### F3.3 — LangGraph Migration Assessment

**Valor:** Evaluar si LangGraph mejora la mantenibilidad y extensibilidad del pipeline.

**User Stories:**
- As a developer, I want explicit state machine modeling, so that pipeline flow is declarative and extensible.

**Acceptance Criteria:**
- Spike: reimplementar pipeline actual en LangGraph
- Comparar: lines of code, testability, debugging experience
- Decision doc: migrate / don't migrate con justificación

---

## 5. Dependencias técnicas

### Infraestructura

| Necesidad | Para qué | Fase |
|-----------|----------|------|
| PostgreSQL instance | Persistencia | F1 |
| Redis instance | Cache + rate limiting distribuido + sessions | F1 |
| TLS certificate | HTTPS | F0 |
| Docker registry | CI/CD image storage | F1 |
| Prometheus + Grafana | Observabilidad | F1 |
| Dominio + DNS | Producción pública | F0 |

### Integraciones

| Servicio | Estado actual | Acción necesaria |
|----------|---------------|-----------------|
| OpenAI API | Funcional | Monitoring de costes (F1.4) |
| Google Places API | Funcional (opt-in) | Monitoring + intent routing (F2.1) |
| Google Routes API | Funcional (opt-in) | Monitoring |
| OpenRouteService | Funcional (opt-in) | Monitoring |
| Overpass/OSM | Funcional (opt-in) | Monitoring |
| Azure Speech Services | Funcional | Monitoring |
| Nominatim | Funcional | Migrar cache a Redis (F1.2) |

### Cambios arquitectónicos

| Cambio | Impacto | Fase |
|--------|---------|------|
| DI root relocation (`shared/` → `application/`) | Bajo — imports update | F0 |
| Simulation extraction del adapter | Bajo — nueva clase + DI config | F0 |
| DB-backed ConversationService | Medio — nueva implementación de `ConversationInterface` | F1 |
| Redis cache abstraction | Medio — `CacheInterface` + adapter para geocoding/NLU | F1 |
| Intent-based routing en pipeline | Medio — condicional en `_execute_pipeline_async()` | F2 |
| Streaming endpoint | Medio — nuevo endpoint SSE + frontend EventSource | F2 |

---

## 6. Riesgos técnicos y mitigaciones

| # | Riesgo | Impacto | Mitigación |
|---|--------|---------|------------|
| R1 | OpenAI rate limits o downtime durante producción | Respuestas degradadas o timeout | Circuit breaker ya existe; añadir fallback a respuesta cached o mensaje "servicio temporalmente no disponible" |
| R2 | Google API cost overrun con tráfico real | Factura inesperada | `BudgetTracker` ya implementado; configurar alertas en F1.4; intent routing (F2.1) reduce calls 40-60% |
| R3 | Migración de persistencia rompe conversaciones existentes | Pérdida de datos de sesión | In-memory actual no persiste — no hay datos que migrar. Clean start |
| R4 | spaCy model download en cold start (50-100MB) | Latencia en primer request post-deploy | Pre-download en Docker build stage; lazy loading ya implementado en `SpacyNERService` |
| R5 | Prompt injection via NLU input | LLM ejecuta instrucciones maliciosas | Input sanitization en F0; guardrails en system prompt; evaluar output filtering |
| R6 | Token consumption del LLM alto con pipeline completo | Coste elevado por request | Intent routing (F2.1) reduce prompt size; `llm_max_tokens: 2500` ya limita output |
| R7 | Overpass API rate limits (1 req/s sin key) | Fallback constante a local data | `CachedGeocodingService` con TTL ya mitiga parcialmente; Redis cache (F1.2) lo elimina |
| R8 | Breaking changes en Google Places API (New) v1 | Tools dejan de funcionar | Interfaces ABC + factories aíslan el cambio; fallback automático a `local` ya existe |

---

## 7. Priorización

| Feature | Prioridad | Justificación |
|---------|-----------|---------------|
| F0.1 API Key Auth | **P0** | Sin auth, el sistema es explotable. Bloqueante para producción |
| F0.2 Inbound Rate Limiting | **P0** | Complementa auth; previene abuso incluso con key válida |
| F0.3 HTTPS + CORS | **P0** | Requisito legal (GDPR) y de seguridad básica |
| F0.4 Frontend Logging Cleanup | **P1** | Profesionaliza la UX; trivial de implementar |
| F0.5 Extract Simulation | **P1** | Mejora mantenibilidad; desbloquea testing del adapter real |
| F0.6 DI Relocation | **P1** | Corrige layer violation; bajo riesgo |
| F1.1 PostgreSQL Persistence | **P0** | Sin persistencia no hay producto viable |
| F1.2 Redis Cache | **P1** | Reduce costes API y latencia; prerequisito para rate limiting distribuido |
| F1.3 CI/CD Pipeline | **P0** | Sin CI, cada merge es un riesgo; bloqueante para operación profesional |
| F1.4 Prometheus + Grafana | **P1** | Sin métricas se opera a ciegas en producción |
| F1.5 Correlation IDs | **P1** | Prerequisito para debugging eficiente en producción |
| F2.1 Intent Routing | **P2** | Mayor impacto en coste/latencia post-launch |
| F2.2 Profile Ranking | **P2** | Feature diferenciador del producto |
| F2.3 Query Builder | **P2** | Mejora calidad de búsqueda |
| F2.4 User Location | **P2** | Mejora relevancia significativamente |
| F2.5 LLM Streaming | **P2** | Mejora UX percibida drásticamente |
| F3.1 Multi-Tenant | **P3** | Solo si modelo de negocio lo requiere |
| F3.2 i18n | **P3** | Expansión de mercado |
| F3.3 LangGraph Assessment | **P3** | Exploración técnica; no bloquea nada |

---

## 8. Estimación relativa

| Feature | Estimación | Notas |
|---------|-----------|-------|
| F0.1 API Key Auth | **M** (3-5d) | `AuthInterface` ya definida; middleware + storage + CLI |
| F0.2 Inbound Rate Limiting | **S** (1-2d) | `slowapi` integration o reutilizar patrón de `resilience.py` |
| F0.3 HTTPS + CORS | **S** (1-2d) | Config-only si hay load balancer; certbot si bare metal |
| F0.4 Frontend Logging | **S** (1-2d) | Wrapper + find/replace en 7 archivos |
| F0.5 Extract Simulation | **S** (1-2d) | Move code + nueva clase + DI switch |
| F0.6 DI Relocation | **S** (1d) | Move file + update imports |
| F1.1 PostgreSQL | **L** (1-2w) | Schema design + SQLAlchemy models + Alembic + migration + tests |
| F1.2 Redis Cache | **M** (3-5d) | `CacheInterface` + Redis adapter + migrate geocoding/NLU cache |
| F1.3 CI/CD | **M** (3-5d) | GitHub Actions workflow + Docker build + staging deploy |
| F1.4 Prometheus + Grafana | **M** (3-5d) | Instrumentation + dashboard design + alerting rules |
| F1.5 Correlation IDs | **S** (1-2d) | Middleware + structlog contextvars |
| F2.1 Intent Routing | **M** (3-5d) | Intent→tools mapping + conditional pipeline + tests + metrics |
| F2.2 Profile Ranking | **L** (1-2w) | PlacesSearchTool changes + ranking logic + profile test dataset |
| F2.3 Query Builder | **M** (3-5d) | Normalization module + dedup + evaluation dataset |
| F2.4 User Location | **M** (3-5d) | Frontend component exists; backend integration + PlacesSearchTool wiring |
| F2.5 LLM Streaming | **L** (1-2w) | SSE endpoint + LangChain streaming + frontend EventSource + fallback |
| F3.1 Multi-Tenant | **XL** (>2w) | JWT + tenant isolation + DB partitioning + config per tenant |
| F3.2 i18n | **L** (1-2w) | NLU/NER multilang + prompts + UI translation + detection |
| F3.3 LangGraph Assessment | **M** (3-5d) | Spike implementation + comparison doc |

**Total estimado:**
- Fase 0: ~2 semanas
- Fase 1: ~4-5 semanas
- Fase 2: ~5-6 semanas
- Fase 3: ~6+ semanas (según prioridades de negocio)

---

## 9. Quick Wins

Acciones que reducen riesgo o mejoran estabilidad con mínimo esfuerzo:

| Quick Win | Esfuerzo | Impacto | Feature relacionada |
|-----------|----------|---------|-------------------|
| Configurar `cors_origins` con dominio real en `.env` de producción | 5 min | Cierra vector de ataque CORS | F0.3 |
| Cambiar `version: "1.0.0"` en `settings.py` a `"2.1.0"` | 1 min | Coherencia con docs | TD-05 |
| Ejecutar `pytest --cov` y documentar coverage real | 10 min | Baseline para CI | F1.3 |
| Eliminar `AuthInterface` y `StorageInterface` sin implementación | 15 min | Elimina dead code que confunde | TD-06 |
| Añadir `.env.production.example` con config restrictiva | 15 min | Guía de deploy seguro | F0.3 |
| Pinear `debug: false` en config de producción Docker | 5 min | Desactiva reload, verbose logging | F0.3 |
| Añadir `--no-cache` a Overpass requests para evitar stale data | 15 min | Mejora freshness de datos accesibilidad | F2.3 |

---

**Documento generado:** 2026-03-11
**Basado en:** [AUDIT_2026_03_11.md](../Reviews/AUDIT_2026_03_11.md)
