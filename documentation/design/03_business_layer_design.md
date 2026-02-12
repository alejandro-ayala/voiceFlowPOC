# Software Design Document: Business Layer

**Capa**: Logica de negocio (`business/`)
**Fecha**: 12 de Febrero de 2026
**Estado**: Implementado - Framework reutilizable + Dominio turismo

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
│       │   ├── nlu_tool.py                # TourismNLUTool
│       │   ├── accessibility_tool.py      # AccessibilityAnalysisTool
│       │   ├── route_planning_tool.py     # RoutePlanningTool
│       │   └── tourism_info_tool.py       # TourismInfoTool
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

    async def process_request(self, user_input: str) -> AgentResponse:
        return await asyncio.to_thread(self.process_request_sync, user_input)

    @abstractmethod
    def _execute_pipeline(self, user_input: str) -> dict[str, str]: ...

    @abstractmethod
    def _build_response_prompt(self, user_input: str, tool_results: dict[str, str]) -> str: ...
```

**Patron**: Template Method - el algoritmo fijo (pipeline -> prompt -> LLM -> history) esta en la base; los hooks (`_execute_pipeline`, `_build_response_prompt`) los define cada dominio.

**Async**: `process_request()` delega via `asyncio.to_thread()`, compatible con FastAPI sin problemas de event loop.

## 4. Dominio Tourism (`business/domains/tourism/`)

### 4.1 `agent.py` - Orquestador de turismo

```python
class TourismMultiAgent(MultiAgentOrchestrator):
    def __init__(self, openai_api_key=None):
        llm = ChatOpenAI(model="gpt-4", temperature=0.3, max_tokens=1500)
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)
        self.nlu = TourismNLUTool()
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()

    def _execute_pipeline(self, user_input: str) -> dict[str, str]:
        nlu_result = self.nlu._run(user_input)
        accessibility_result = self.accessibility._run(nlu_result)
        route_result = self.route._run(accessibility_result)
        tourism_result = self.tourism_info._run(nlu_result)
        return {
            "nlu": nlu_result,
            "accessibility": accessibility_result,
            "route": route_result,
            "tourism_info": tourism_result,
        }

    def _build_response_prompt(self, user_input, tool_results):
        return build_response_prompt(user_input=user_input, tool_results=tool_results)
```

### 4.2 Tools

Cada tool extiende `langchain.tools.BaseTool` con:
- `name: str` - Identificador
- `description: str` - Descripcion para el LLM
- `_run()` - Ejecucion sincrona
- `_arun()` - Async (delega a `_run()`)

| Tool | Archivo | Input | Output |
|------|---------|-------|--------|
| NLU | `tools/nlu_tool.py` | Texto del usuario | Intent, entities, accessibility type |
| Accesibilidad | `tools/accessibility_tool.py` | Resultado NLU (JSON) | Score, facilities, certification |
| Rutas | `tools/route_planning_tool.py` | Resultado accesibilidad (JSON) | Rutas metro/bus, costes |
| Info turistica | `tools/tourism_info_tool.py` | Resultado NLU (JSON) | Horarios, precios, servicios |

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
| `response_prompt.py` | `build_response_prompt(user_input, tool_results)` - Construye prompt final con resultados de las 4 tools |

## 5. Diagrama de flujo

```
Usuario: "Como llego al Museo del Prado en silla de ruedas?"
                    |
                    v
    MultiAgentOrchestrator.process_request()  [core/]
                    |
                    v (via asyncio.to_thread)
    TourismMultiAgent._execute_pipeline()     [domains/tourism/]
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
    NLU Tool   Accessibility  Route Planning
    (intent)     (score)       (transport)
        |           |           |
        v           |           |
    Tourism Info    |           |
    (horarios)      |           |
        |           |           |
        +-----------+-----------+
                    |
                    v
    TourismMultiAgent._build_response_prompt() [domains/tourism/prompts/]
                    |
                    v
    ChatOpenAI GPT-4 genera respuesta conversacional
                    |
                    v
    AgentResponse(response_text, tool_results) [core/models.py]
```

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
| `asyncio.run()` incompatible con FastAPI | `asyncio.to_thread()` en orchestrator base |
| Tests en codigo de produccion | Eliminados del modulo |
| Placeholders vacios (`nlp/`, `tourism/`) | Eliminados |
| Framework no reutilizable | `core/` generico, `domains/` especifico |

## 11. Deuda tecnica pendiente

1. **Orquestacion secuencial fija**: `_execute_pipeline()` ejecuta siempre los 4 tools; podria ser selectiva segun intent
2. **Simulacion en adapter**: `_simulate_ai_response()` (~110 lineas hardcodeadas) deberia estar en un mock service separado
3. **Sin modelos de dominio tipados**: Los resultados de tools son JSON strings, no dataclasses
4. **Sin tests unitarios**: Estructura preparada pero 0% coverage
