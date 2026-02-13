# Propuesta: Fase 2B - Descomposicion de Business Layer (Framework Reutilizable)

**Fecha**: 12 de Febrero de 2026
**Estado**: ✅ IMPLEMENTADA (12 Feb 2026)
**Branch**: `feature/docker-migration`

---

## 1. Contexto y problema

El archivo `business/ai_agents/langchain_agents.py` es un monolito de 751 lineas que contiene:

- 4 clases de herramientas LangChain (`TourismNLUTool`, `AccessibilityAnalysisTool`, `RoutePlanningTool`, `TourismInfoTool`)
- 1 clase orquestadora (`TourismMultiAgent`)
- ~340 lineas (~45%) de datos hardcodeados de turismo Madrid (diccionarios de venues, rutas, accesibilidad)
- Prompts del sistema y de respuesta embebidos en metodos
- 2 funciones de test (`test_individual_tools`, `test_orchestrator`) en codigo de produccion
- Bloque `if __name__` con logica de ejecucion

**Problemas concretos:**

1. **SRP violado**: Cada tool mezcla parsing, logica de negocio y datos estaticos en `_run()`
2. **Datos acoplados**: `accessibility_db`, `route_db`, `venue_db` (~340 lineas) inline dentro de metodos
3. **Sin interfaz formal**: `TourismMultiAgent` no implementa ninguna interfaz; el adapter usa `hasattr()` con 5 fallbacks
4. **Orquestacion fija**: `process_request()` ejecuta siempre los 4 tools en orden fijo
5. **Prompts hardcodeados**: system prompt y response prompt como strings embebidos
6. **`asyncio.run()` problematico**: `process_request_sync()` usa `asyncio.run()` que falla si ya hay un event loop (FastAPI)
7. **Tests en produccion**: funciones de test que no pertenecen al modulo

---

## 2. Requisito clave: Reutilizabilidad

> *"Esta capa se usara en este proyecto como PoC, pero su objetivo es mas amplio: tener una capa que pueda usarse de manera transversal en distintos proyectos con agentes IA. Si manana empiezo un nuevo proyecto de planes de entrenamiento MTB, sea mas una cuestion de modificar configuraciones/prompts que de rehacer codigo."*

Esto implica separar claramente:

| Que | Reutilizable? | Ejemplo |
|-----|--------------|---------|
| Orquestacion LLM (ejecutar tools, invocar LLM, gestionar conversacion) | **Si** | Identico para turismo, MTB, o cualquier dominio |
| Implementacion de tools (que hace cada tool) | **No** | NLU turismo != NLU MTB |
| Datos de dominio (venues, rutas, patrones NLU) | **No** | Madrid != rutas MTB |
| Prompts (system prompt, response template) | **No** | Turismo accesible != entrenamiento |

---

## 3. Arquitectura propuesta

```
business/
├── __init__.py
│
├── core/                              # ── FRAMEWORK REUTILIZABLE ──
│   ├── __init__.py                    #     (identico para cualquier proyecto)
│   ├── interfaces.py                  # MultiAgentInterface (ABC)
│   ├── orchestrator.py                # MultiAgentOrchestrator (clase base)
│   └── models.py                      # AgentResponse (modelo generico)
│
├── domains/                           # ── IMPLEMENTACIONES POR DOMINIO ──
│   ├── __init__.py
│   └── tourism/                       # Dominio actual: turismo accesible Madrid
│       ├── __init__.py                # Exports: TourismMultiAgent
│       ├── agent.py                   # TourismMultiAgent(MultiAgentOrchestrator)
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── nlu_tool.py            # TourismNLUTool (solo logica NLU)
│       │   ├── accessibility_tool.py  # AccessibilityAnalysisTool (solo logica)
│       │   ├── route_planning_tool.py # RoutePlanningTool (solo logica)
│       │   └── tourism_info_tool.py   # TourismInfoTool (solo logica)
│       ├── data/
│       │   ├── __init__.py
│       │   ├── nlu_patterns.py        # Patrones de keywords para NLU
│       │   ├── accessibility_data.py  # Base de datos de accesibilidad
│       │   ├── route_data.py          # Base de datos de rutas
│       │   └── venue_data.py          # Base de datos de venues
│       └── prompts/
│           ├── __init__.py
│           ├── system_prompt.py       # SYSTEM_PROMPT constant
│           └── response_prompt.py     # build_response_prompt() function
│
├── ai_agents/                         # ── BACKWARD COMPATIBILITY ──
│   ├── __init__.py                    # Re-exports: TourismMultiAgent
│   └── langchain_agents.py            # Facade: re-export desde domains/tourism
│
├── nlp/                               # ELIMINAR (placeholder vacio)
└── tourism/                           # ELIMINAR (placeholder vacio)
```

### 3.1 Analogia: Nuevo proyecto MTB

Para un nuevo proyecto de entrenamiento MTB, se crearia:

```
business/domains/mtb/
├── __init__.py
├── agent.py                   # MTBTrainingAgent(MultiAgentOrchestrator)
├── tools/
│   ├── fitness_assessment.py  # FitnessAssessmentTool
│   ├── training_plan.py       # TrainingPlanTool
│   └── route_difficulty.py    # RouteDifficultyTool
├── data/
│   ├── training_zones.py      # Zonas de entrenamiento
│   └── difficulty_data.py     # Datos de dificultad
└── prompts/
    ├── system_prompt.py       # Prompt de entrenador MTB
    └── response_prompt.py     # Template de respuesta MTB
```

**Sin tocar `business/core/`** - el framework se reutiliza intacto.

---

## 4. Componentes del Core (Framework reutilizable)

### 4.1 `core/interfaces.py` - Contrato generico

```python
from abc import ABC, abstractmethod
from typing import Any

class MultiAgentInterface(ABC):
    """Contrato para cualquier sistema multi-agente basado en LLM."""

    @abstractmethod
    def process_request_sync(self, user_input: str) -> "AgentResponse":
        """Procesa una consulta de forma sincrona."""
        ...

    @abstractmethod
    async def process_request(self, user_input: str) -> "AgentResponse":
        """Procesa una consulta de forma asincrona."""
        ...

    @abstractmethod
    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Retorna el historial de conversacion."""
        ...

    @abstractmethod
    def clear_conversation(self) -> None:
        """Limpia el historial de conversacion."""
        ...
```

### 4.2 `core/models.py` - Modelos genericos

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentResponse:
    """Respuesta generica de cualquier agente multi-tool."""
    response_text: str                         # Respuesta en lenguaje natural
    tool_results: dict[str, str]               # {nombre_tool: resultado_json}
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 4.3 `core/orchestrator.py` - Clase base

```python
class MultiAgentOrchestrator(MultiAgentInterface):
    """
    Orquestador base para sistemas multi-agente.
    Las subclases definen:
    - _execute_pipeline(): que tools ejecutar y en que orden
    - _build_response_prompt(): como construir el prompt de sintesis
    """

    def __init__(self, llm, system_prompt: str):
        self.llm = llm
        self.system_prompt = system_prompt
        self.conversation_history: list[dict[str, str]] = []

    def process_request_sync(self, user_input: str) -> AgentResponse:
        """Ejecuta pipeline + LLM de forma sincrona."""
        tool_results = self._execute_pipeline(user_input)
        prompt = self._build_response_prompt(user_input, tool_results)
        response = self.llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        self.conversation_history.append({"user": user_input, "assistant": text})
        return AgentResponse(response_text=text, tool_results=tool_results)

    async def process_request(self, user_input: str) -> AgentResponse:
        """Ejecuta pipeline + LLM de forma asincrona (via thread)."""
        return await asyncio.to_thread(self.process_request_sync, user_input)

    # ── Hooks para subclases ──

    @abstractmethod
    def _execute_pipeline(self, user_input: str) -> dict[str, str]:
        """Define que tools ejecutar y como encadenarlas."""
        ...

    @abstractmethod
    def _build_response_prompt(self, user_input: str, tool_results: dict[str, str]) -> str:
        """Define como construir el prompt de sintesis para el LLM."""
        ...

    # ── Gestion de conversacion (comun a todos los dominios) ──

    def get_conversation_history(self) -> list[dict[str, Any]]:
        return [{"user": m["user"], "assistant": m["assistant"]} for m in self.conversation_history]

    def clear_conversation(self) -> None:
        self.conversation_history = []
```

**Mejoras respecto al monolito actual:**
- `process_request_sync()` ya NO usa `asyncio.run()` (que fallaba con event loop activo de FastAPI)
- `process_request()` async usa `asyncio.to_thread()` (patron correcto para FastAPI)
- La gestion de conversacion e invocacion LLM es reutilizable sin duplicar codigo

---

## 5. Dominio Tourism: Que cambia

### 5.1 Extraccion de datos (~340 lineas)

Los diccionarios de datos se mueven a `domains/tourism/data/`:

| Origen en langchain_agents.py | Destino | Variables |
|-------------------------------|---------|-----------|
| Lineas 43-80 (keyword lists en NLUTool) | `data/nlu_patterns.py` | `INTENT_PATTERNS`, `DESTINATION_PATTERNS`, `ACCESSIBILITY_PATTERNS` |
| Lineas 128-183 (accessibility_db en AccessibilityTool) | `data/accessibility_data.py` | `ACCESSIBILITY_DB`, `DEFAULT_ACCESSIBILITY` |
| Lineas 233-337 (route_db en RouteTool) | `data/route_data.py` | `ROUTE_DB`, `DEFAULT_ROUTE` |
| Lineas 387-531 (venue_db en TourismInfoTool) | `data/venue_data.py` | `VENUE_DB`, `DEFAULT_VENUE` |

### 5.2 Extraccion de prompts

| Origen | Destino | Contenido |
|--------|---------|-----------|
| Lineas 583-594 (`self.system_prompt` en `__init__`) | `prompts/system_prompt.py` | `SYSTEM_PROMPT` constant |
| Lineas 642-666 (`final_prompt` en `process_request`) | `prompts/response_prompt.py` | `build_response_prompt(user_input, tool_results)` |

### 5.3 Tools separadas

Cada tool se mueve a su archivo en `domains/tourism/tools/`. La logica se simplifica separando datos de lógica:

**Antes** (todo en `_run()`):
```python
class TourismNLUTool(BaseTool):
    def _run(self, user_input):
        # 40 lineas de keyword matching inline
        # datos y logica mezclados
```

**Despues** (`nlu_tool.py`):
```python
from business.domains.tourism.data.nlu_patterns import INTENT_PATTERNS, DESTINATION_PATTERNS, ACCESSIBILITY_PATTERNS

class TourismNLUTool(BaseTool):
    def _run(self, user_input):
        user_lower = user_input.lower()
        intent = self._match_pattern(user_lower, INTENT_PATTERNS, "information_request")
        destination = self._match_pattern(user_lower, DESTINATION_PATTERNS, "general")
        accessibility = self._match_pattern(user_lower, ACCESSIBILITY_PATTERNS, "general")
        # construir resultado JSON

    @staticmethod
    def _match_pattern(text, patterns, default):
        for name, keywords in patterns.items():
            if any(kw in text for kw in keywords):
                return name
        return default
```

### 5.4 TourismMultiAgent (`agent.py`)

```python
class TourismMultiAgent(MultiAgentOrchestrator):
    """Orquestador especifico de turismo accesible en Madrid."""

    def __init__(self, openai_api_key=None):
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found.")
        llm = ChatOpenAI(model="gpt-4", temperature=0.3, openai_api_key=api_key, max_tokens=1500)
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)

        # Tools del dominio turismo
        self.nlu = TourismNLUTool()
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()

    def _execute_pipeline(self, user_input):
        """Pipeline especifico de turismo: NLU -> Accesibilidad -> Rutas + Info."""
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

---

## 6. Cambios en capas existentes

### 6.1 `shared/interfaces/interfaces.py`

Anadir import de `MultiAgentInterface` para que la application layer pueda usarla via DI:

```python
from business.core.interfaces import MultiAgentInterface  # noqa: F401
```

### 6.2 `application/orchestration/backend_adapter.py`

Eliminar la cadena de `hasattr()` con 5 fallbacks:

```python
# ANTES (fragil, reflection-based):
if hasattr(backend, "process_request_sync"):
    response = await asyncio.to_thread(backend.process_request_sync, transcription)
elif hasattr(backend, "process_request"):
    response = await asyncio.to_thread(backend.process_request, transcription)
elif hasattr(backend, "process_query"):
    ...  # 3 fallbacks mas

# DESPUES (contrato claro):
result = await backend.process_request(transcription)
response = result.response_text
```

### 6.3 `business/ai_agents/` - Backward compatibility

```python
# business/ai_agents/langchain_agents.py (facade de 1 linea)
from business.domains.tourism.agent import TourismMultiAgent  # noqa: F401

# business/ai_agents/__init__.py (sin cambios funcionales)
from business.domains.tourism.agent import TourismMultiAgent
__all__ = ["TourismMultiAgent"]
```

Cualquier codigo que importe `from business.ai_agents.langchain_agents import TourismMultiAgent` sigue funcionando.

---

## 7. Limpieza

- **Eliminar** `business/nlp/` (directorio placeholder vacio, nunca se uso)
- **Eliminar** `business/tourism/` (directorio placeholder vacio, nunca se uso)
- **Eliminar** funciones `test_individual_tools()` y `test_orchestrator()` del codigo de produccion
- **Eliminar** bloque `if __name__ == "__main__"` de langchain_agents.py

---

## 8. Resumen de archivos

| Archivo | Accion | Descripcion |
|---------|--------|-------------|
| `business/core/__init__.py` | CREAR | Exports del framework |
| `business/core/interfaces.py` | CREAR | MultiAgentInterface (ABC) |
| `business/core/models.py` | CREAR | AgentResponse (dataclass) |
| `business/core/orchestrator.py` | CREAR | MultiAgentOrchestrator (clase base) |
| `business/domains/__init__.py` | CREAR | Package init |
| `business/domains/tourism/__init__.py` | CREAR | Exports: TourismMultiAgent |
| `business/domains/tourism/agent.py` | CREAR | TourismMultiAgent(MultiAgentOrchestrator) |
| `business/domains/tourism/tools/__init__.py` | CREAR | Exports: 4 tools |
| `business/domains/tourism/tools/nlu_tool.py` | CREAR | TourismNLUTool |
| `business/domains/tourism/tools/accessibility_tool.py` | CREAR | AccessibilityAnalysisTool |
| `business/domains/tourism/tools/route_planning_tool.py` | CREAR | RoutePlanningTool |
| `business/domains/tourism/tools/tourism_info_tool.py` | CREAR | TourismInfoTool |
| `business/domains/tourism/data/__init__.py` | CREAR | Package init |
| `business/domains/tourism/data/nlu_patterns.py` | CREAR | Patrones NLU extraidos |
| `business/domains/tourism/data/accessibility_data.py` | CREAR | DB accesibilidad extraida |
| `business/domains/tourism/data/route_data.py` | CREAR | DB rutas extraida |
| `business/domains/tourism/data/venue_data.py` | CREAR | DB venues extraida |
| `business/domains/tourism/prompts/__init__.py` | CREAR | Package init |
| `business/domains/tourism/prompts/system_prompt.py` | CREAR | SYSTEM_PROMPT |
| `business/domains/tourism/prompts/response_prompt.py` | CREAR | build_response_prompt() |
| `business/ai_agents/langchain_agents.py` | REEMPLAZAR | Facade de 1 linea |
| `business/ai_agents/__init__.py` | MODIFICAR | Import path actualizado |
| `business/__init__.py` | MODIFICAR | Actualizar __all__ |
| `application/orchestration/backend_adapter.py` | MODIFICAR | Eliminar hasattr chain |
| `shared/interfaces/interfaces.py` | MODIFICAR | Anadir re-export |
| `business/nlp/` | ELIMINAR | Placeholder vacio |
| `business/tourism/` | ELIMINAR | Placeholder vacio |

**Total: ~20 archivos nuevos, ~5 archivos modificados, 2 directorios eliminados**

---

## 9. Verificacion

1. **Imports funcionales**: `python -c "from business.domains.tourism.agent import TourismMultiAgent"`
2. **Backward compat**: `python -c "from business.ai_agents.langchain_agents import TourismMultiAgent"`
3. **Core reutilizable**: `python -c "from business.core.orchestrator import MultiAgentOrchestrator"`
4. **Lint + format**: `poetry run ruff check . && poetry run ruff format --check .`
5. **App arranca**: `docker compose up --build` -> health check en `/api/v1/health/`
6. **Tests existentes**: `poetry run pytest tests/ -v` (si hay)

---

## 10. Riesgos y mitigacion

| Riesgo | Mitigacion |
|--------|-----------|
| Imports circulares (business -> shared -> business) | `shared/interfaces/` solo importa tipos con TYPE_CHECKING |
| LangChain BaseTool con Pydantic fields | Mantener firma identica al separar clases |
| Romper `from business.ai_agents.langchain_agents import TourismMultiAgent` | Facade de re-export en langchain_agents.py |
| `asyncio.run()` vs event loop FastAPI | Eliminado: nueva base usa `asyncio.to_thread()` |

---
---

# SDD: Business Layer (Post-Refactor Fase 2B)

**Capa**: Logica de negocio (`business/`)
**Fecha**: 12 de Febrero de 2026
**Estado**: Pendiente implementacion
**Reemplaza**: Seccion 2 del SDD `03_business_layer_design.md` (estado monolito)

---

## SDD-1. Proposito

La capa `business/` contiene la logica de dominio del sistema. Tras el refactor Fase 2B, se divide en dos niveles:

- **`core/`**: Framework reutilizable de orquestacion multi-agente LLM. No contiene logica de dominio. Puede usarse en cualquier proyecto que necesite coordinar herramientas LLM.
- **`domains/tourism/`**: Implementacion concreta del dominio de turismo accesible en Madrid. Contiene las tools, datos y prompts especificos de este PoC.

---

## SDD-2. Estructura de directorios (post-refactor)

```
business/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── interfaces.py
│   ├── orchestrator.py
│   └── models.py
├── domains/
│   ├── __init__.py
│   └── tourism/
│       ├── __init__.py
│       ├── agent.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── nlu_tool.py
│       │   ├── accessibility_tool.py
│       │   ├── route_planning_tool.py
│       │   └── tourism_info_tool.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── nlu_patterns.py
│       │   ├── accessibility_data.py
│       │   ├── route_data.py
│       │   └── venue_data.py
│       └── prompts/
│           ├── __init__.py
│           ├── system_prompt.py
│           └── response_prompt.py
└── ai_agents/
    ├── __init__.py
    └── langchain_agents.py
```

---

## SDD-3. Componentes: Core (`business/core/`)

### SDD-3.1 `interfaces.py` - Contrato multi-agente

| Interfaz | Metodos | Implementada por | Estado |
|----------|---------|------------------|--------|
| `MultiAgentInterface` | `process_request_sync()`, `process_request()`, `get_conversation_history()`, `clear_conversation()` | `MultiAgentOrchestrator` (base), `TourismMultiAgent` (concreta) | Post-refactor |

**Firmas detalladas:**

```python
from abc import ABC, abstractmethod
from typing import Any

from business.core.models import AgentResponse


class MultiAgentInterface(ABC):
    """Contrato generico para cualquier sistema multi-agente basado en LLM."""

    @abstractmethod
    def process_request_sync(self, user_input: str) -> AgentResponse:
        """Procesa una consulta de forma sincrona.
        Ejecuta pipeline de tools + invocacion LLM.
        """
        ...

    @abstractmethod
    async def process_request(self, user_input: str) -> AgentResponse:
        """Procesa una consulta de forma asincrona.
        Wrapper async sobre process_request_sync via asyncio.to_thread.
        """
        ...

    @abstractmethod
    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Retorna historial de conversacion como lista de {user, assistant}."""
        ...

    @abstractmethod
    def clear_conversation(self) -> None:
        """Limpia el historial de conversacion."""
        ...
```

### SDD-3.2 `models.py` - Modelos genericos

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResponse:
    """Respuesta estandar de cualquier agente multi-tool.

    Attributes:
        response_text: Respuesta final en lenguaje natural generada por el LLM.
        tool_results: Resultados intermedios de cada tool {nombre: json_string}.
        metadata: Informacion adicional opcional (timestamps, metricas, etc).
    """

    response_text: str
    tool_results: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)
```

### SDD-3.3 `orchestrator.py` - Clase base del orquestador

```python
import asyncio
from abc import abstractmethod
from typing import Any

import structlog

from business.core.interfaces import MultiAgentInterface
from business.core.models import AgentResponse

logger = structlog.get_logger(__name__)


class MultiAgentOrchestrator(MultiAgentInterface):
    """
    Orquestador base para sistemas multi-agente con LLM.

    Responsabilidades (reutilizables):
    - Invocar el LLM con un prompt construido a partir de resultados de tools
    - Gestionar historial de conversacion
    - Proveer wrapper sync/async

    Responsabilidades delegadas a subclases:
    - _execute_pipeline(): Define que tools ejecutar y como encadenarlas
    - _build_response_prompt(): Define como construir el prompt de sintesis
    """

    def __init__(self, llm, system_prompt: str):
        self.llm = llm
        self.system_prompt = system_prompt
        self.conversation_history: list[dict[str, str]] = []

    def process_request_sync(self, user_input: str) -> AgentResponse:
        logger.info("Processing request", input=user_input)
        tool_results = self._execute_pipeline(user_input)
        prompt = self._build_response_prompt(user_input, tool_results)
        response = self.llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        self.conversation_history.append({"user": user_input, "assistant": text})
        logger.info("Request processed", response_length=len(text))
        return AgentResponse(response_text=text, tool_results=tool_results)

    async def process_request(self, user_input: str) -> AgentResponse:
        return await asyncio.to_thread(self.process_request_sync, user_input)

    def get_conversation_history(self) -> list[dict[str, Any]]:
        return [
            {"user": m["user"], "assistant": m["assistant"]}
            for m in self.conversation_history
        ]

    def clear_conversation(self) -> None:
        self.conversation_history = []
        logger.info("Conversation history cleared")

    @abstractmethod
    def _execute_pipeline(self, user_input: str) -> dict[str, str]:
        """Ejecuta las tools del dominio. Retorna {nombre_tool: resultado_json}."""
        ...

    @abstractmethod
    def _build_response_prompt(
        self, user_input: str, tool_results: dict[str, str]
    ) -> str:
        """Construye el prompt final para la invocacion LLM."""
        ...
```

**Template Method Pattern:** `process_request_sync()` define el algoritmo fijo (pipeline -> prompt -> LLM -> historial), mientras que `_execute_pipeline()` y `_build_response_prompt()` son los pasos variables que cada dominio sobreescribe.

---

## SDD-4. Componentes: Dominio Tourism (`business/domains/tourism/`)

### SDD-4.1 `agent.py` - Orquestador de turismo

| Clase | Hereda de | Responsabilidad |
|-------|-----------|-----------------|
| `TourismMultiAgent` | `MultiAgentOrchestrator` | Configura LLM (GPT-4), instancia las 4 tools de turismo, define el pipeline especifico y el prompt de respuesta |

```python
import os
from typing import Optional

from langchain_openai import ChatOpenAI

from business.core.orchestrator import MultiAgentOrchestrator
from business.domains.tourism.prompts.system_prompt import SYSTEM_PROMPT
from business.domains.tourism.prompts.response_prompt import build_response_prompt
from business.domains.tourism.tools.nlu_tool import TourismNLUTool
from business.domains.tourism.tools.accessibility_tool import AccessibilityAnalysisTool
from business.domains.tourism.tools.route_planning_tool import RoutePlanningTool
from business.domains.tourism.tools.tourism_info_tool import TourismInfoTool


class TourismMultiAgent(MultiAgentOrchestrator):
    """Orquestador del dominio turismo accesible Madrid."""

    def __init__(self, openai_api_key: Optional[str] = None):
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable."
            )
        llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            openai_api_key=api_key,
            max_tokens=1500,
        )
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

    def _build_response_prompt(
        self, user_input: str, tool_results: dict[str, str]
    ) -> str:
        return build_response_prompt(
            user_input=user_input, tool_results=tool_results
        )
```

### SDD-4.2 Tools (Herramientas especializadas)

Cada tool hereda de `langchain.tools.BaseTool` y sigue el patron:
- `name: str` - Identificador
- `description: str` - Descripcion para el LLM
- `_run(input: str) -> str` - Logica sincrona, retorna JSON string
- `_arun(input: str) -> str` - Delega a `_run()`

| Clase | Archivo | Input | Output (JSON) | Datos que consulta |
|-------|---------|-------|---------------|--------------------|
| `TourismNLUTool` | `tools/nlu_tool.py` | `user_input` (texto libre) | `{intent, entities, confidence, timestamp}` | `nlu_patterns.py` |
| `AccessibilityAnalysisTool` | `tools/accessibility_tool.py` | `nlu_result` (JSON del NLU) | `{accessibility_level, score, facilities, certification}` | `accessibility_data.py` |
| `RoutePlanningTool` | `tools/route_planning_tool.py` | `accessibility_result` (JSON de accessibility) | `{routes[], alternatives, cost}` | `route_data.py` |
| `TourismInfoTool` | `tools/tourism_info_tool.py` | `nlu_result` (JSON del NLU) | `{venue, hours, pricing, reviews, services}` | `venue_data.py` |

**Patron comun de cada tool:**

```python
class <ToolName>(BaseTool):
    name: str = "<tool_name>"
    description: str = "<descripcion>"

    def _run(self, input_data: str) -> str:
        # 1. Parsear input (JSON o texto)
        # 2. Consultar datos importados desde data/
        # 3. Construir resultado
        # 4. Retornar JSON string
        return json.dumps(result, indent=2, ensure_ascii=False)

    async def _arun(self, input_data: str) -> str:
        return self._run(input_data)
```

### SDD-4.3 Datos de dominio (`data/`)

| Modulo | Variables exportadas | Tipo | Lineas aprox. |
|--------|---------------------|------|---------------|
| `nlu_patterns.py` | `INTENT_PATTERNS`, `DESTINATION_PATTERNS`, `ACCESSIBILITY_PATTERNS` | `dict[str, list[str]]` | ~40 |
| `accessibility_data.py` | `ACCESSIBILITY_DB`, `DEFAULT_ACCESSIBILITY` | `dict[str, dict]` | ~55 |
| `route_data.py` | `ROUTE_DB`, `DEFAULT_ROUTE` | `dict[str, dict]` | ~105 |
| `venue_data.py` | `VENUE_DB`, `DEFAULT_VENUE` | `dict[str, dict]` | ~145 |

Cada modulo exporta constantes `dict` con datos estaticos. Los defaults se usan cuando el destino no se encuentra en la base de datos.

### SDD-4.4 Prompts (`prompts/`)

| Modulo | Exporta | Descripcion |
|--------|---------|-------------|
| `system_prompt.py` | `SYSTEM_PROMPT: str` | Instrucciones del sistema para el LLM. Define el rol (asistente de turismo accesible), idioma (espanol), y enfoque (accesibilidad). |
| `response_prompt.py` | `build_response_prompt(user_input, tool_results) -> str` | Funcion que construye el prompt final de sintesis. Recibe la pregunta del usuario y los resultados de las 4 tools, y genera un prompt que instruye al LLM a componer una respuesta coherente. |

---

## SDD-5. Diagrama de flujo (post-refactor)

```
Usuario: "¿Como llego al Museo del Prado en silla de ruedas?"
                    │
    ┌───────────────┴────────────────┐
    │  Application Layer             │
    │  LocalBackendAdapter           │
    │    await agent.process_request()│
    └───────────────┬────────────────┘
                    │
    ┌───────────────┴────────────────┐
    │  Core: MultiAgentOrchestrator  │
    │  process_request_sync()        │
    │                                │
    │  1. _execute_pipeline()  ──────┼──► Delegado a TourismMultiAgent
    │  2. _build_response_prompt()───┼──► Delegado a TourismMultiAgent
    │  3. llm.invoke(prompt)         │
    │  4. Guardar en historial       │
    │  5. return AgentResponse       │
    └───────────────┬────────────────┘
                    │
    ┌───────────────┴────────────────────────────────────┐
    │  Domain: TourismMultiAgent._execute_pipeline()     │
    │                                                    │
    │  user_input ──► TourismNLUTool ──┬── nlu_result    │
    │                                  │                 │
    │              nlu_result ──► AccessibilityTool       │
    │                                  │                 │
    │       accessibility_result ──► RoutePlanningTool    │
    │                                  │                 │
    │              nlu_result ──► TourismInfoTool         │
    │                                  │                 │
    │  return {nlu, accessibility, route, tourism_info}  │
    └────────────────────────────────────────────────────┘
                    │
    ┌───────────────┴────────────────────────────────────┐
    │  Domain: build_response_prompt()                   │
    │                                                    │
    │  Combina user_input + 4 tool results en un prompt  │
    │  que instruye al LLM a generar respuesta final     │
    └────────────────────────────────────────────────────┘
                    │
                    ▼
    Respuesta en espanol con recomendaciones de
    accesibilidad, rutas y horarios
```

### SDD-5.1 Pipeline de tools (grafo de dependencias)

```
                    user_input
                        │
                        ▼
                 ┌─────────────┐
                 │ TourismNLU  │
                 │   Tool      │
                 └──────┬──────┘
                        │ nlu_result
               ┌────────┴────────┐
               │                 │
               ▼                 ▼
    ┌──────────────────┐  ┌──────────────┐
    │ Accessibility    │  │ TourismInfo  │
    │   Tool           │  │   Tool       │
    └────────┬─────────┘  └──────────────┘
             │ accessibility_result
             ▼
    ┌──────────────────┐
    │ RoutePlanning    │
    │   Tool           │
    └──────────────────┘
```

**Nota**: `TourismInfoTool` y `AccessibilityAnalysisTool` reciben ambos `nlu_result` pero se ejecutan secuencialmente (no en paralelo). `RoutePlanningTool` depende del resultado de `AccessibilityAnalysisTool`.

---

## SDD-6. Invocacion desde Application Layer (post-refactor)

### SDD-6.1 `backend_adapter.py` simplificado

```python
# application/orchestration/backend_adapter.py

class LocalBackendAdapter(BackendInterface):

    async def _get_backend_instance(self):
        if self._backend_instance is None:
            from business.domains.tourism.agent import TourismMultiAgent
            self._backend_instance = TourismMultiAgent()
        return self._backend_instance

    async def _process_real_query(self, transcription: str) -> str:
        agent = await self._get_backend_instance()
        # Contrato claro: process_request retorna AgentResponse
        result = await agent.process_request(transcription)
        return result.response_text
```

**Cambio clave**: Se elimina la cadena de `hasattr()` con 5 fallbacks. El contrato `MultiAgentInterface.process_request()` garantiza que el metodo existe y retorna `AgentResponse`.

### SDD-6.2 DI (Dependency Injection)

```python
# shared/utils/dependencies.py (sin cambios funcionales)
def get_backend_adapter(settings=Depends(get_settings)) -> BackendInterface:
    return LocalBackendAdapter(settings)
```

La `BackendInterface` sigue siendo el contrato de la application layer. `LocalBackendAdapter` internamente usa `MultiAgentInterface` para comunicarse con el agente. Esto mantiene la separacion de capas.

---

## SDD-7. Dependencias externas

| Paquete | Version | Usado en | Para que |
|---------|---------|----------|----------|
| `langchain` | 0.1.0 | `domains/tourism/tools/*.py` | `BaseTool` base class |
| `langchain-openai` | 0.0.5 | `domains/tourism/agent.py` | `ChatOpenAI` (GPT-4) |
| `structlog` | 23.2.0 | `core/orchestrator.py`, tools | Logging estructurado |
| `python-dotenv` | 1.0.0 | `domains/tourism/agent.py` | Cargar `.env` |

**Requiere**: `OPENAI_API_KEY` en variables de entorno (solo para modo real; modo simulado no invoca al agente).

**Nota**: `core/` solo depende de `structlog`. No tiene dependencia directa de LangChain. Las tools de dominio si dependen de LangChain `BaseTool`, pero el orquestador base es agnostico al framework.

---

## SDD-8. Principios SOLID aplicados

| Principio | Aplicacion |
|-----------|-----------|
| **SRP** | Cada tool en su archivo con una unica responsabilidad. Datos separados de logica. Prompts separados de orquestacion. |
| **OCP** | Nuevo dominio = nueva carpeta en `domains/`. No se modifica `core/`. Nuevas tools aniadibles sin modificar el agent existente. |
| **LSP** | `TourismMultiAgent` es sustituible por cualquier `MultiAgentOrchestrator` en el adapter. |
| **ISP** | `MultiAgentInterface` expone solo 4 metodos esenciales. Las tools no exponen interfaz propia hacia capas superiores (solo el orquestador). |
| **DIP** | `LocalBackendAdapter` depende de `BackendInterface` (abstraccion), no de `TourismMultiAgent` (concrecion). El orquestador base depende de hooks abstractos (`_execute_pipeline`), no de tools concretas. |

---

## SDD-9. Deuda tecnica resuelta y pendiente

### Resuelta con Fase 2B

| # | Deuda | Resolucion |
|---|-------|-----------|
| 1 | Monolito de 751 lineas | Descompuesto en ~20 modulos especializados |
| 2 | Datos hardcodeados en metodos | Extraidos a `data/` (4 modulos) |
| 3 | Sin interfaz formal | `MultiAgentInterface` en `core/interfaces.py` |
| 4 | `hasattr()` chain en adapter | Eliminada; usa contrato `process_request() -> AgentResponse` |
| 5 | `asyncio.run()` problematico | Reemplazado por `asyncio.to_thread()` en base |
| 6 | Prompts embebidos en codigo | Extraidos a `prompts/` (2 modulos) |
| 7 | Tests en codigo de produccion | Eliminados (se moveran a `tests/` en Fase 3) |
| 8 | Directorios placeholder vacios | `nlp/` y `tourism/` eliminados |

### Pendiente (Fases futuras)

| # | Deuda | Fase |
|---|-------|------|
| 1 | Datos estaticos en Python dicts (podrian ser JSON/YAML externos) | Fase 4+ |
| 2 | NLU basado en keywords (sin ML real) | Fase 4+ |
| 3 | Pipeline secuencial fijo (tools siempre se ejecutan todas) | Fase 4+ |
| 4 | Sin tests unitarios para tools individuales | Fase 3 |
| 5 | Sin fallback en business layer si LLM falla | Fase 3 |
