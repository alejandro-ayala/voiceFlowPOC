# Software Design Document: Business Layer

**Capa**: Logica de negocio (`business/`)
**Fecha**: 5 de Marzo de 2026
**Estado**: Implementado - Framework reutilizable + Dominio turismo (actualizado Post Fase 0 + Fase 1)

---

## 1. Proposito

La capa `business/` contiene la logica de dominio del sistema: el procesamiento de consultas mediante un sistema multi-agente LangChain. Esta organizada como un **framework reutilizable** (`core/`) con implementaciones especificas por dominio (`domains/`).

## 2. Estructura actual

### 2.1 Directorio

```
business/
├── __init__.py
├── core/                                  # FRAMEWORK REUTILIZABLE
│   ├── __init__.py                        # Exports: MultiAgentInterface, AgentResponse, MultiAgentOrchestrator
│   ├── interfaces.py                      # MultiAgentInterface (ABC)
│   ├── orchestrator.py                    # MultiAgentOrchestrator (Template Method base)
│   └── models.py                          # AgentResponse (dataclass)
│
├── domains/                               # IMPLEMENTACIONES POR DOMINIO
│   └── tourism/                           # Dominio actual: turismo accesible Madrid
│       ├── __init__.py                    # Exports: TourismMultiAgent
│       ├── agent.py                       # TourismMultiAgent(MultiAgentOrchestrator)
│       ├── tools/
│       │   ├── __init__.py                # Exports: todas las tools
│       │   ├── nlu_tool.py                # TourismNLUTool (Foundation)
│       │   ├── location_ner_tool.py       # LocationNERTool (Foundation)
│       │   ├── places_search_tool.py      # PlacesSearchTool (Phase 1)
│       │   ├── directions_tool.py         # DirectionsTool (Phase 1)
│       │   ├── accessibility_enrichment_tool.py  # AccessibilityEnrichmentTool (Phase 1)
│       │   ├── accessibility_tool.py      # AccessibilityAnalysisTool (Legacy)
│       │   ├── route_planning_tool.py     # RoutePlanningTool (Legacy)
│       │   └── tourism_info_tool.py       # TourismInfoTool (Legacy)
│       ├── data/
│       │   ├── __init__.py
│       │   ├── nlu_patterns.py            # INTENT_PATTERNS, DESTINATION_PATTERNS, etc.
│       │   ├── accessibility_data.py      # ACCESSIBILITY_DB
│       │   ├── route_data.py              # ROUTE_DB
│       │   └── venue_data.py              # VENUE_DB
│       └── prompts/
│           ├── __init__.py
│           ├── system_prompt.py           # SYSTEM_PROMPT
│           └── response_prompt.py         # build_response_prompt()
│
└── ai_agents/                             # BACKWARD COMPATIBILITY
    ├── __init__.py                        # Re-export: TourismMultiAgent
    └── langchain_agents.py                # Facade: re-export desde domains/tourism
```

### 2.2 Principio de separacion

| Capa | Contenido | Reutilizable? |
|------|-----------|---------------|
| `core/` | Orquestacion LLM, gestion de conversacion, modelos base, interfaz abstracta | **Si** - identico para cualquier proyecto |
| `domains/tourism/` | Tools, datos Madrid, prompts turismo | **No** - especifico del PoC |
| `ai_agents/` | Re-exports para no romper imports existentes | Temporal - backward compat |

Para un nuevo dominio (ej. planes de entrenamiento MTB), se crearia `domains/mtb/` con sus tools y prompts, reutilizando `core/` intacto.

## 3. Core Framework (`business/core/`)

### 3.1 `interfaces.py` - Contrato generico

```python
class MultiAgentInterface(ABC):
    """Contrato para cualquier sistema multi-agente."""

    @abstractmethod
    def process_request_sync(self, user_input: str) -> AgentResponse: ...

    @abstractmethod
    async def process_request(self, user_input: str) -> AgentResponse: ...

    @abstractmethod
    def get_conversation_history(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def clear_conversation(self) -> None: ...
```

### 3.2 `models.py` - Modelos genericos

```python
@dataclass
class AgentResponse:
    response_text: str
    tool_results: dict[str, str]       # {tool_name: json_result}
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 3.3 `orchestrator.py` - Base reutilizable (Template Method)

```python
class MultiAgentOrchestrator(MultiAgentInterface):
    """Orquestador base - subclases definen pipeline y prompts."""

    def __init__(self, llm, system_prompt: str):
        self.llm = llm
        self.system_prompt = system_prompt
        self.conversation_history: list[dict[str, str]] = []

    def process_request_sync(self, user_input: str) -> AgentResponse:
        tool_results = self._execute_pipeline(user_input)
        prompt = self._build_response_prompt(user_input, tool_results)
        response = self.llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        self.conversation_history.append({"user": user_input, "assistant": text})
        return AgentResponse(response_text=text, tool_results=tool_results)

    async def process_request(self, user_input: str, **kwargs) -> AgentResponse:
        # Fase 0: async-native — sin asyncio.to_thread()
        tool_results, metadata = await self._execute_pipeline_async(user_input, **kwargs)
        prompt = self._build_response_prompt(user_input, tool_results, **kwargs)
        response = await asyncio.to_thread(self.llm.invoke, prompt)
        text = response.content if hasattr(response, "content") else str(response)
        self.conversation_history.append({"user": user_input, "assistant": text})
        return AgentResponse(response_text=text, tool_results=tool_results, metadata=metadata)

    @abstractmethod
    async def _execute_pipeline_async(self, user_input: str, **kwargs) -> tuple[dict, dict]: ...

    @abstractmethod
    def _build_response_prompt(self, user_input: str, tool_results: dict[str, str], **kwargs) -> str: ...
```

**Patron**: Template Method - el algoritmo fijo (pipeline -> prompt -> LLM -> history) esta en la base; los hooks (`_execute_pipeline_async`, `_build_response_prompt`) los define cada dominio.

**Async**: Pipeline es async-native (`await` directo). Solo la llamada a `llm.invoke()` usa `asyncio.to_thread()` para no bloquear el event loop. Se eliminó el `asyncio.to_thread()` del pipeline completo (resuelto en Fase 0).

## 4. Dominio Tourism (`business/domains/tourism/`)

### 4.1 `agent.py` - Orquestador de turismo

```python
class TourismMultiAgent(MultiAgentOrchestrator):
    def __init__(
        self,
        openai_api_key=None,
        ner_service=None,          # NERServiceInterface (Fase 0)
        nlu_service=None,          # NLUServiceInterface (Fase 0)
        places_service=None,       # PlacesServiceInterface (Fase 1)
        directions_service=None,   # DirectionsServiceInterface (Fase 1)
        accessibility_service=None,# AccessibilityServiceInterface (Fase 1)
    ):
        llm = ChatOpenAI(model="gpt-4", temperature=0.3, max_tokens=2500)
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)
        # Foundation tools (always available)
        self.nlu = TourismNLUTool(nlu_service=nlu_service)
        self.location_ner = LocationNERTool(ner_service=ner_service)
        # Phase 1 domain tools (created when services injected)
        self._places_tool = PlacesSearchTool(places_service) if places_service else None
        self._directions_tool = DirectionsTool(directions_service) if directions_service else None
        self._accessibility_enrichment_tool = (
            AccessibilityEnrichmentTool(accessibility_service) if accessibility_service else None
        )
        # Legacy tools (fallback when no services injected)
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()

    async def _execute_pipeline_async(self, user_input, profile_context=None):
        ctx = ToolPipelineContext(user_input=user_input, profile_context=profile_context)
        # Step 1: NLU + NER in parallel (async-native)
        nlu_ctx, ner_ctx = await asyncio.gather(
            self.nlu.execute(ctx.model_copy()), self.location_ner.execute(ctx.model_copy())
        )
        ctx = ctx.merge(nlu_ctx, ner_ctx)  # merge results
        # Step 2: Domain tools (Phase 1 if available, otherwise legacy)
        if self._places_tool:
            ctx = await self._places_tool.execute(ctx)
            ctx = await self._accessibility_enrichment_tool.execute(ctx)
            ctx = await self._directions_tool.execute(ctx)
        else:
            # Legacy sequential pipeline (BaseTool._run)
            ...
        return tool_results, metadata

    def _build_response_prompt(self, user_input, tool_results, profile_context=None):
        return build_response_prompt(
            user_input=user_input, tool_results=tool_results, profile_context=profile_context
        )
```

### 4.2 Tools

#### Foundation Tools
Extienden `langchain.tools.BaseTool` con firma `execute(ctx: ToolPipelineContext) -> ToolPipelineContext`:

| Tool | Archivo | Input | Output |
|------|---------|-------|--------|
| NLU | `tools/nlu_tool.py` | `ctx.user_input` | `ctx.nlu_result` (NLUResult) |
| Location NER | `tools/location_ner_tool.py` | `ctx.user_input` | `ctx.resolved_entities` (ResolvedEntities) |

#### Phase 1 Domain Tools (API-First)
Operan sobre `ToolPipelineContext` con firma `execute(ctx) -> ctx`. Reciben servicio externo por DI:

| Tool | Archivo | Servicio DI | Popula en ctx |
|------|---------|-------------|---------------|
| Places Search | `tools/places_search_tool.py` | `PlacesServiceInterface` | `ctx.place`, `ctx.venue_detail` |
| Accessibility Enrichment | `tools/accessibility_enrichment_tool.py` | `AccessibilityServiceInterface` | `ctx.accessibility` |
| Directions | `tools/directions_tool.py` | `DirectionsServiceInterface` | `ctx.routes` |

Errores parciales se registran en `ctx.errors` como `ToolError` sin romper el pipeline.

#### Legacy Tools (backward compat)
Solo se usan si no se inyectan servicios Phase 1. Extienden `langchain.tools.BaseTool` con `_run()`/`_arun()`:

| Tool | Archivo | Nota |
|------|---------|------|
| Accesibilidad | `tools/accessibility_tool.py` | Lookup en `ACCESSIBILITY_DB` |
| Rutas | `tools/route_planning_tool.py` | Lookup en `ROUTE_DB` |
| Info turistica | `tools/tourism_info_tool.py` | Lookup en `VENUE_DB` |

### 4.3 Datos estaticos (`data/`)

Los datos de Madrid estan separados en modulos independientes:

| Modulo | Contenido | Entries |
|--------|-----------|---------|
| `nlu_patterns.py` | `INTENT_PATTERNS`, `DESTINATION_PATTERNS`, `ACCESSIBILITY_PATTERNS`, `MADRID_GENERAL_KEYWORDS`, `MADRID_SPECIFIC_EXCLUSIONS` | ~30 patrones |
| `accessibility_data.py` | `ACCESSIBILITY_DB`, `DEFAULT_ACCESSIBILITY` | 4 venues |
| `route_data.py` | `ROUTE_DB`, `DEFAULT_ROUTE` | 3 destinos |
| `venue_data.py` | `VENUE_DB`, `DEFAULT_VENUE` | 4 venues con horarios, precios, servicios |

### 4.4 Prompts (`prompts/`)

| Modulo | Contenido |
|--------|-----------|
| `system_prompt.py` | `SYSTEM_PROMPT` - Instrucciones del asistente de turismo accesible |
| `response_prompt.py` | `build_response_prompt(user_input, tool_results)` - Construye prompt final con resultados de las 5 tools |

## 5. Diagrama de flujo

```
Usuario: "Como llego al Museo del Prado en silla de ruedas?"
                    |
                    v
    MultiAgentOrchestrator.process_request()  [core/]
                    |
                    v (async-native, sin asyncio.to_thread)
    TourismMultiAgent._execute_pipeline_async()  [domains/tourism/]
                    |
        +-----------+-----------+   Step 1: await asyncio.gather()
        |                       |
        v                       v
    NLU Tool              LocationNER Tool
    (intent, entities)    (locations, top_location)
        |                       |
        +-----------+-----------+
                    |
                    v               Step 2: secuencial (Phase 1 tools)
            PlacesSearchTool        → ctx.place, ctx.venue_detail
                    |
                    v
        AccessibilityEnrichmentTool → ctx.accessibility
                    |
                    v
            DirectionsTool          → ctx.routes
                    |
                    v
    TourismMultiAgent._build_response_prompt() [domains/tourism/prompts/]
                    |
                    v
    ChatOpenAI GPT-4 genera respuesta conversacional
                    |
                    v
    AgentResponse(response_text, tool_results, metadata) [core/models.py]
```

**Nota:** `ToolPipelineContext` (Pydantic) fluye como acumulador tipado entre todas las tools. Cada tool lee/escribe campos específicos del contexto.

## 6. Invocacion desde Application Layer

```python
# application/orchestration/backend_adapter.py
class LocalBackendAdapter(BackendInterface):
    async def _process_real_query(self, transcription: str) -> str:
        agent = await self._get_backend_instance()  # TourismMultiAgent()
        result = await agent.process_request(transcription)
        return result.response_text
```

El adapter usa directamente el contrato `MultiAgentInterface.process_request()` que retorna `AgentResponse`. Sin reflection, sin `hasattr()`.

## 7. Dependencias externas

```python
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
```

**Requiere:** `OPENAI_API_KEY` en variables de entorno (solo cuando `USE_REAL_AGENTS=true`).

**Nota:** La integracion con OpenAI se hace exclusivamente a traves de LangChain en `domains/tourism/agent.py`.

## 8. Patrones de diseno

| Patron | Componente | Descripcion |
|--------|-----------|-------------|
| Template Method | `MultiAgentOrchestrator` | Algoritmo fijo en base, hooks abstractos en subclases |
| Strategy | `_execute_pipeline()` / `_build_response_prompt()` | Cada dominio define su propia estrategia |
| Facade | `ai_agents/langchain_agents.py` | Re-export de 1 linea para backward compat |
| Abstract Factory | `core/interfaces.py` | Contrato que permite inyectar cualquier implementacion |

## 9. Estrategia de testing

```python
# Test tools individuales (sin LLM)
def test_nlu_tool_detects_prado():
    tool = TourismNLUTool()
    result = json.loads(tool._run("museo del prado accesible"))
    assert result["entities"]["destination"] == "Museo del Prado"

# Test orchestrator con LLM mockeado
def test_orchestrator_pipeline():
    agent = TourismMultiAgent()
    results = agent._execute_pipeline("museo del prado")
    assert "nlu" in results
    assert "accessibility" in results

# Test de integracion (consume tokens - solo CI con flag)
@pytest.mark.integration
async def test_full_query_with_openai():
    agent = TourismMultiAgent()
    result = await agent.process_request("museo del prado accesible")
    assert len(result.response_text) > 0
    assert isinstance(result, AgentResponse)
```

## 10. Deuda tecnica resuelta (Fase 2B)

Los siguientes problemas fueron resueltos en la Fase 2B:

| Problema anterior | Solucion aplicada |
|-------------------|-------------------|
| Monolito 751 lineas | Descompuesto en ~20 archivos modulares |
| Datos hardcodeados en metodos | Extraidos a `domains/tourism/data/` |
| Prompts embebidos en codigo | Extraidos a `domains/tourism/prompts/` |
| Sin interfaz formal | `MultiAgentInterface` (ABC) en `core/` |
| `hasattr()` chain en adapter | Contrato directo `process_request() -> AgentResponse` |
| `asyncio.run()` incompatible con FastAPI | Pipeline async-native con `await` directo (Fase 0); `asyncio.to_thread()` solo para `llm.invoke()` |
| Tests en codigo de produccion | Eliminados del modulo |
| Placeholders vacios (`nlp/`, `tourism/`) | Eliminados |
| Framework no reutilizable | `core/` generico, `domains/` especifico |

## 11. Deuda tecnica pendiente

1. **Orquestacion fija por etapas**: NLU+NER corren en paralelo, pero el pipeline sigue fijo y podria ser selectivo segun intent (Fase 2)
2. **Simulacion en adapter**: `_simulate_ai_response()` (~110 lineas hardcodeadas) deberia estar en un mock service separado
3. ~~**Sin modelos de dominio tipados**~~: ✅ Resuelto en Fase 0 — `ToolPipelineContext` con 6 modelos Pydantic (`NLUResult`, `ResolvedEntities`, `PlaceCandidate`, `AccessibilityInfo`, `RouteOption`, `VenueDetail`)
4. ~~**Sin tests unitarios**~~: ✅ Resuelto — 128 tests pasan (Fase 0: 12, Fase 1: 42, existentes: 86)
