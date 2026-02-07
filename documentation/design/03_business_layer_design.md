# Software Design Document: Business Layer

**Capa**: Lógica de negocio (`business/`)
**Fecha**: 4 de Febrero de 2026
**Estado**: Implementado como monolito - Pendiente descomposición

---

## 1. Propósito

La capa `business/` contiene la lógica de dominio del sistema: el procesamiento de consultas turísticas mediante un sistema multi-agente LangChain que orquesta herramientas especializadas en NLU, accesibilidad, rutas y turismo.

## 2. Estado actual

### 2.1 Estructura de directorios

```
business/
├── __init__.py
├── ai_agents/
│   ├── __init__.py          # Re-export: TourismMultiAgent
│   └── langchain_agents.py  # Monolito (~400 líneas, 5 clases + 2 funciones)
├── nlp/
│   └── __init__.py           # PLACEHOLDER VACÍO
└── tourism/
    └── __init__.py           # PLACEHOLDER VACÍO
```

### 2.2 `langchain_agents.py` - Monolito Multi-Agente

El archivo contiene toda la lógica de negocio en un solo módulo:

#### Clases

| Clase | Hereda de | Responsabilidad |
|-------|-----------|-----------------|
| `TourismNLUTool` | `BaseTool` (LangChain) | Análisis de lenguaje natural: detecta intención, entidades y idioma |
| `AccessibilityAnalysisTool` | `BaseTool` | Análisis de accesibilidad para destinos turísticos |
| `RoutePlanningTool` | `BaseTool` | Planificación de rutas accesibles con transporte |
| `TourismInfoTool` | `BaseTool` | Información turística general sobre destinos |
| `TourismMultiAgent` | - | Orquestador que coordina las 4 tools mediante LangChain Agent |

#### TourismMultiAgent (Orquestador)

```python
class TourismMultiAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.3)
        self.tools = [
            TourismNLUTool(),
            AccessibilityAnalysisTool(),
            RoutePlanningTool(),
            TourismInfoTool()
        ]
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )

    async def process_query(self, query: str) -> str:
        # Ejecuta el agente LangChain con la query del usuario
        # El agente decide qué tools usar basándose en el prompt

    def process_request(self, query: str) -> str:
        # Versión síncrona del procesamiento
```

#### Tools (Herramientas especializadas)

Cada tool es una clase LangChain `BaseTool` con:
- `name`: Identificador de la herramienta
- `description`: Descripción que el LLM usa para decidir cuándo invocarla
- `_run()`: Método síncrono de ejecución
- `_arun()`: Método asíncrono (delega a `_run()`)

**TourismNLUTool:**
```python
name = "tourism_nlu_analysis"
# Analiza la consulta del usuario para detectar:
# - Intención (accessibility_info, route_planning, tourism_info, general)
# - Entidades (ubicaciones, tipos de accesibilidad, preferencias)
# - Idioma detectado
# Output: JSON con intent, entities, language, confidence
```

**AccessibilityAnalysisTool:**
```python
name = "accessibility_analysis"
# Evalúa la accesibilidad de un destino turístico:
# - Puntuación de accesibilidad (1-10)
# - Tipos de accesibilidad disponibles
# - Certificaciones
# - Recomendaciones
# Output: JSON con accessibility_score, features, certifications
```

**RoutePlanningTool:**
```python
name = "route_planning"
# Planifica rutas accesibles:
# - Opciones de transporte (metro, bus, taxi)
# - Accesibilidad de cada opción
# - Tiempo estimado y coste
# Output: JSON con routes[], cada una con transport, time, cost, accessibility
```

**TourismInfoTool:**
```python
name = "tourism_information"
# Proporciona información turística general:
# - Horarios de apertura
# - Precios
# - Descripción del lugar
# - Puntos de interés cercanos
# Output: JSON con destination_info, hours, prices, nearby
```

#### Funciones de test

```python
async def test_individual_tools():
    # Prueba cada tool de forma aislada con queries de ejemplo

async def test_orchestrator():
    # Prueba el orquestador completo con una query de turismo accesible
```

### 2.3 Dependencias externas

```python
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import BaseTool
```

**Requiere:** `OPENAI_API_KEY` en variables de entorno.

**Nota:** La integración con OpenAI se hace exclusivamente a través de LangChain, no existe un cliente OpenAI dedicado en `integration/external_apis/`.

## 3. Diagrama de flujo

```
Usuario: "¿Cómo llego al Museo del Prado en silla de ruedas?"
                    │
                    ▼
        TourismMultiAgent.process_query()
                    │
                    ▼
        LangChain Agent (GPT-4)
        "Necesito analizar esta consulta"
                    │
        ┌───────────┼───────────────┐
        │           │               │
        ▼           ▼               ▼
    NLU Tool   Accessibility   Route Planning
    (intent)     (score)        (transport)
        │           │               │
        └───────────┼───────────────┘
                    │
                    ▼
        LangChain Agent compone respuesta final
                    │
                    ▼
        Texto con recomendaciones de accesibilidad,
        rutas de transporte y puntuaciones
```

## 4. Invocación desde Application Layer

```python
# application/orchestration/backend_adapter.py
class LocalBackendAdapter(BackendInterface):
    async def _process_real_query(self, transcription: str) -> str:
        backend = await self._get_backend_instance()  # TourismMultiAgent()
        # Busca método compatible: process_request_sync, process_request,
        # process_query, process, run (en ese orden)
        response = await asyncio.to_thread(backend.process_request, transcription)
        return str(response)
```

**Observación:** El adapter usa reflection (`hasattr`) para buscar un método compatible, lo que indica acoplamiento frágil. Debería definirse una interfaz clara para el multi-agent.

## 5. Plan de descomposición (Fase 2B)

### 5.1 Estructura objetivo

```
business/
├── __init__.py
├── ai_agents/
│   ├── __init__.py
│   ├── coordinator.py          # TourismMultiAgent (solo orquestación)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── nlu_tool.py         # TourismNLUTool
│   │   ├── accessibility_tool.py  # AccessibilityAnalysisTool
│   │   ├── route_tool.py       # RoutePlanningTool
│   │   └── tourism_info_tool.py   # TourismInfoTool
│   └── config/
│       ├── __init__.py
│       └── prompts.py          # Prompts extraídos (actualmente hardcoded)
├── tourism/
│   ├── accessibility_rules.py  # Reglas de accesibilidad (extraídas de prompts)
│   └── domain_models.py        # Modelos de dominio (Destination, Route, etc.)
└── nlp/
    └── intent_classifier.py    # Si se quiere NLU sin LLM para casos simples
```

### 5.2 Beneficios de la descomposición

1. **Testing independiente:** Cada tool testeable con LLM mockeado
2. **Prompts versionables:** Extraídos a archivos configurables
3. **Reglas de negocio explícitas:** Accesibilidad y turismo en código, no en prompts
4. **OCP:** Nuevas tools añadibles sin modificar coordinator.py
5. **Reutilización:** Tools usables fuera del contexto LangChain

### 5.3 Interfaz propuesta para el coordinador

```python
class TourismAgentInterface(ABC):
    """Interfaz para business layer - añadir a shared/interfaces/"""

    @abstractmethod
    async def process_query(self, query: str) -> AgentResponse:
        """Procesa una consulta turística y devuelve respuesta estructurada"""
        pass

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """Lista las herramientas disponibles"""
        pass

@dataclass
class AgentResponse:
    text: str
    intent: str
    entities: Dict[str, Any]
    tools_used: List[str]
    confidence: float
```

## 6. Estrategia de testing

```python
# Test con LLM mockeado (no consume tokens)
@pytest.fixture
def mock_llm():
    return MockChatOpenAI(responses=["respuesta mock"])

def test_nlu_tool_detects_accessibility_intent():
    tool = TourismNLUTool()
    # Mock del LLM interno
    result = tool._run("museo accesible")
    assert "accessibility" in result

def test_coordinator_uses_correct_tools():
    agent = TourismMultiAgent()
    # Verificar que una query de rutas invoca RoutePlanningTool

# Test de integración (consume tokens - solo en CI con flag)
@pytest.mark.integration
def test_full_query_with_openai():
    agent = TourismMultiAgent()
    result = await agent.process_query("museo del prado accesible")
    assert len(result) > 0
```

## 7. Deuda técnica identificada

1. **Monolito:** Todo en un archivo de ~400 líneas
2. **Prompts hardcoded:** Las descripciones y comportamiento de cada tool están en strings dentro del código Python
3. **Sin interfaz formal:** `TourismMultiAgent` no implementa ninguna interfaz de `shared/`, el adapter usa reflection
4. **Lógica de dominio en prompts:** Las reglas de accesibilidad, puntuaciones y criterios de turismo son texto enviado al LLM, no código verificable
5. **Sin fallback sin LLM:** Si OpenAI no está disponible, toda la capa business falla. El fallback está en `backend_adapter.py` (respuestas hardcodeadas), no aquí
6. **`test_individual_tools` y `test_orchestrator`** son funciones de test dentro del código de producción. Deberían moverse a `tests/`
7. **`nlp/` y `tourism/`** son directorios vacíos que sugieren una arquitectura que no existe
