# Multi-Agent Architecture VoiceFlow STT + LangChain

**Date**: November 28, 2025  
**Version**: 2.0 - LangChain Multi-Agent Integration

## 📋 Project Context

This project implements a **Multi-Agent Speech-to-Text (STT) and Accessible Tourism System** using **LangChain** as the main orchestrator. It is an evolution of the original PoC toward a productive system that combines voice processing with conversational artificial intelligence.

### Main Objective
Create a complete multi-agent system that can:
- Capture and process voice in real time (Spanish)
- Transcribe using Azure Speech Services
- Process requests through specialized LangChain agents
- Generate contextually relevant accessible tourism recommendations

## 🎯 LangChain Multi-Agent Architecture

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     VOICEFLOW STT MULTI-AGENT SYSTEM                        │
└─────────────────────────────────────────────────────────────────────────────┘

 🎙️ USER VOICE (Spanish)
         │
         ▼
┌─────────────────────┐
│   AUDIO SERVICE     │ ◄── INDEPENDENT SERVICE (Current Implementation)
│                     │     
│ • Microphone Capture│     record_user_audio()
│ • WAV Processing    │     ↓
│ • Azure STT         │     transcribe_user_input()  
│ • Quality Control   │     
└─────────────────────┘
         │
         ▼ [Spanish text transcription]
┌─────────────────────────────────────────────────────────────────────────────┐
│                 🧠 LANGCHAIN ORCHESTRATOR AGENT                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   ChatOpenAI (GPT-4) + Memory                      │    │
│  │                                                                     │    │
│  │  INPUT: "Necesito una ruta accesible al Museo del Prado"          │    │
│  │  TASK: Analyze → Plan → Execute → Respond                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                      TOOL SELECTION & ORCHESTRATION                        │
│                                    │                                        │
│       ┌────────────────────────────┼────────────────────────────┐           │
│       │                            │                            │           │
│       ▼                            ▼                            ▼           │
│  ┌─────────────┐              ┌─────────────┐              ┌─────────────┐    │
│  │ 🧠 NLU TOOL │              │♿ ACCESS TOOL│              │🗺️ ROUTE TOOL│    │
│  │             │              │             │              │             │    │
│  │ • Intent    │              │ • Disability│              │ • Maps API  │    │
│  │   Detection │              │   Analysis  │              │ • Route Opt │    │
│  │ • Entity    │              │ • Access    │              │ • Transport │    │
│  │   Extraction│              │   Requirements              │   Integration│    │
│  │ • Confidence│              │ • Preferences│              │ • Time Opt  │    │
│  └─────────────┘              └─────────────┘              └─────────────┘    │
│       │                            │                            │           │
│       └────────────────────────────┼────────────────────────────┘           │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    RESPONSE SYNTHESIS                               │    │
│  │                                                                     │    │
│  │  • Combine all tool results                                        │    │
│  │  • Generate conversational response                                 │    │
│  │  • Create actionable recommendations                                │    │
│  │  • Maintain conversation context                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
 📋 STRUCTURED RECOMMENDATIONS
 • Accessible routes with ratings
 • Transport options
 • Venue accessibility details
 • Contextual tips and warnings
```

### Respuesta a Preguntas Arquitectónicas:

#### 1. ¿Orquestador Principal?
**SÍ** - **LangChain Agent** actúa como orquestador:
- **Decisor inteligente**: Determina qué herramientas usar y cuándo
- **Gestor de contexto**: Mantiene memoria conversacional
- **Coordinador de flujo**: Orquesta la ejecución de tools de forma dinámica

#### 2. ¿Paralelo o Pipeline?
**HÍBRIDO INTELIGENTE**:
- **Decisión dinámica**: El orquestador decide el flujo según el contexto
- **Paralelo cuando posible**: Análisis NLU + APIs simultáneas
- **Secuencial cuando necesario**: NLU → Accessibility → Route Planning
- **Adaptativo**: El LLM optimiza el flujo según la consulta

#### 3. ¿Integrar STT como Agente?
**NO** - **Mantener como servicio independiente**:
- **Razón**: El STT es infraestructura, no lógica de negocio
- **Ventaja**: Menor latencia, control directo del audio
- **Separación clara**: Audio/STT vs. Procesamiento inteligente

## 🏗️ Componentes Detallados

### 1. Audio Service (Current - Independent Service)
```python
# Keep current implementation - Not a LangChain agent
async def record_user_audio() -> str
async def transcribe_user_input(audio_file: str) -> str
```
**Rationale**: Audio processing is infrastructure, not business logic.

### 2. LangChain Orchestrator Agent
```python
class TourismMultiAgent:
    """Main orchestrator that coordinates all specialized tools"""
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.3)
        self.memory = ConversationBufferWindowMemory(k=10)
        self.tools = [
            TourismNLUTool(),
            AccessibilityAnalysisTool(),
            RoutePlanningTool(),
            TourismInfoTool()
        ]
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True
        )
    
    async def process_request(self, user_input: str) -> str:
        """Process user request through intelligent tool orchestration"""
        return self.agent.run(user_input)
```

### 3. Specialized LangChain Tools

#### 3.1 Tourism NLU Tool
```python
class TourismNLUTool(BaseTool):
    """Extract intents and entities from Spanish tourism requests"""
    name = "tourism_nlu"
    description = "Analyze user intent and extract tourism entities from Spanish text"
    
    def _run(self, user_input: str) -> Dict[str, Any]:
        # Extract: intent, entities, confidence, context
        return {
            "intent": "route_planning",
            "entities": {"destination": "Museo del Prado", "accessibility": "wheelchair"},
            "confidence": 0.95,
            "language": "es"
        }
```

#### 3.2 Accessibility Analysis Tool
```python
class AccessibilityAnalysisTool(BaseTool):
    """Analyze accessibility requirements and provide recommendations"""
    name = "accessibility_analysis"
    description = "Analyze accessibility needs and provide venue/route recommendations"
    
    def _run(self, nlu_result: Dict[str, Any]) -> Dict[str, Any]:
        # Analyze accessibility requirements and provide detailed info
        return {
            "accessibility_level": "full_wheelchair_access",
            "venue_rating": 4.8,
            "facilities": ["wheelchair_ramps", "adapted_bathrooms", "audio_guides"],
            "warnings": []
        }
```

#### 3.3 Route Planning Tool
```python
class RoutePlanningTool(BaseTool):
    """Plan optimal accessible routes using Maps APIs"""
    name = "route_planning"
    description = "Generate accessible routes with transport options"
    
    def _run(self, destination: str, accessibility_req: Dict) -> Dict[str, Any]:
        # Integrate with real Maps APIs for accessible routing
        return {
            "routes": [
                {
                    "transport": "metro",
                    "duration": "25 min",
                    "accessibility": "full",
                    "steps": ["Line 2 to Banco de España", "5 min walk"]
                }
            ],
            "alternatives": ["bus", "taxi"],
            "accessibility_score": 9.2
        }
```

#### 3.4 Tourism Information Tool
```python
class TourismInfoTool(BaseTool):
    """Get real-time tourism information and reviews"""
    name = "tourism_info"
    description = "Fetch current tourism info, schedules, prices, and reviews"
    
    def _run(self, venue: str) -> Dict[str, Any]:
        # Integrate with real tourism APIs
        return {
            "opening_hours": "10:00-20:00",
            "current_price": "15€",
            "accessibility_reviews": ["Great wheelchair access", "Audio guides available"],
            "current_crowds": "moderate",
            "special_exhibitions": ["Velázquez retrospective"]
        }
```

## 🔄 Execution Flow

### Step 1: Audio Processing (Current System)
```python
# 1. Capture audio from microphone
audio_file = await record_user_audio()

# 2. Transcribe using Azure STT
transcription = await transcribe_user_input(audio_file)
```

### Step 2: LangChain Orchestration (New Implementation)
```python
# 3. LangChain agent processes the transcription
response = await tourism_agent.process_request(transcription)

# Internal LangChain flow:
# a) Agent analyzes the request
# b) Determines which tools to use and in what order
# c) Executes tools (can be parallel or sequential)
# d) Synthesizes results into natural language response
```

### Step 3: Response Delivery
```python
# 4. Return structured response to user
print(f"🤖 Assistant: {response}")

# Optional: Convert to speech (future iteration)
# await text_to_speech(response)
```

## 🚀 Implementation Phases

### Phase 1: Template Setup (Current Priority)
- ✅ Update architecture documentation
- 🔄 Update requirements.txt with LangChain dependencies
- 🔄 Implement orchestrator with stub tools
- 🔄 Create integration template that prints data flow

### Phase 2: Tool Implementation
- 🔮 Replace stub tools with real implementations
- 🔮 Integrate external APIs (Maps, Tourism, Reviews)
- 🔮 Add advanced NLU processing
- 🔮 Implement proper error handling

### Phase 3: Production Features
- 🔮 Add conversation memory persistence
- 🔮 Implement response caching
- 🔮 Add performance monitoring
- 🔮 Scale for multiple concurrent users

## 📊 Data Flow Example

**Input**: "Necesito una ruta accesible al Museo del Prado para silla de ruedas"

```
Audio → STT → "Necesito una ruta accesible al Museo del Prado para silla de ruedas"
                                    ↓
                          LangChain Orchestrator
                                    ↓
                    ┌─────────────────────────────────┐
                    │ 1. NLU Analysis                 │
                    │ Intent: route_planning          │
                    │ Entities: {                     │
                    │   destination: "Museo del Prado"│
                    │   accessibility: "wheelchair"   │
                    │ }                               │
                    └─────────────────────────────────┘
                                    ↓
                    ┌─────────────────────────────────┐
                    │ 2. Accessibility Analysis       │
                    │ Requirements: wheelchair_access │
                    │ Venue rating: 4.8/5            │
                    │ Facilities: ramps, bathrooms   │
                    └─────────────────────────────────┘
                                    ↓
                    ┌─────────────────────────────────┐
                    │ 3. Route Planning               │
                    │ Transport: Metro Line 2         │
                    │ Duration: 25 min               │
                    │ Accessibility: Full            │
                    └─────────────────────────────────┘
                                    ↓
                    ┌─────────────────────────────────┐
                    │ 4. Tourism Info                 │
                    │ Hours: 10:00-20:00             │
                    │ Price: 15€                     │
                    │ Current: Velázquez exhibition  │
                    └─────────────────────────────────┘
                                    ↓
                          Response Synthesis
                                    ↓
"Te recomiendo ir al Museo del Prado usando el Metro Línea 2 hasta Banco de España, 
luego 5 minutos caminando. El museo tiene acceso completo para sillas de ruedas, 
con rampas y baños adaptados. Está abierto de 10:00 a 20:00, entrada 15€. 
Actualmente tienen la exposición de Velázquez que vale la pena ver."
```

## 🔧 Technical Decisions

### Why LangChain?
- **Intelligence**: GPT-4 powered decision making
- **Flexibility**: Dynamic tool selection and orchestration  
- **Memory**: Conversation context preservation
- **Extensibility**: Easy to add new tools and capabilities
- **Community**: Rich ecosystem of integrations

### Why Keep STT Separate?
- **Performance**: Direct Azure integration without LLM overhead
- **Reliability**: Proven STT pipeline with error handling
- **Cost**: Avoid unnecessary LLM calls for audio processing
- **Specialization**: Each component does what it does best

### Architecture Benefits
- **Scalable**: Each tool can be scaled independently
- **Testable**: Individual tools can be unit tested
- **Maintainable**: Clear separation of concerns
- **Extensible**: Easy to add new tourism domains or tools
# → Agent analyzes request
# → Selects appropriate tools
# → Executes tools (parallel/sequential)
# → Synthesizes response
```

### Paso 3: Response Generation
```python
# 4. Return structured response
return {
    "recommendations": response.recommendations,
    "conversation_context": response.memory,
    "tools_used": response.tools_executed,
    "accessibility_info": response.accessibility_details
}
```

## 🎯 Principios SOLID en Multi-Agente

### Single Responsibility Principle (SRP)
- **Audio Service**: Solo maneja captura y transcripción
- **LangChain Agent**: Solo orquesta procesamiento inteligente
- **Each Tool**: Una responsabilidad específica

### Open/Closed Principle (OCP)
- **Extensible**: Nuevos tools se agregan sin modificar el orquestador
- **Cerrado**: Core LangChain logic no cambia

### Dependency Inversion Principle (DIP)
- **LangChain abstractions**: Tools implementan BaseTool
- **Service interfaces**: STT services implementan interfaces

## 💡 Ventajas Arquitectónicas

### Escalabilidad
- **Nuevos agentes**: Simplemente agregar tools a la lista
- **APIs adicionales**: Cada tool puede integrar múltiples APIs
- **Complejidad**: LangChain maneja la orquestación compleja

### Mantenibilidad
- **Separación clara**: Audio vs. Procesamiento inteligente
- **Testing**: Cada tool es testeable independientemente
- **Debugging**: LangChain verbose mode para tracing

### Performance
- **Paralelización**: LangChain puede ejecutar tools en paralelo
- **Caching**: Memory para evitar reprocesamiento
- **Optimización**: LLM aprende patrones de uso

## 🔮 Futuras Extensiones

### Agentes Adicionales Posibles
- **WeatherTool**: Condiciones meteorológicas
- **TransportTool**: Opciones de transporte accesible
- **EventsTool**: Eventos y actividades
- **SafetyTool**: Información de seguridad
- **ReviewsTool**: Opinions y ratings en tiempo real

### Capacidades Avanzadas
- **Multi-modal**: Integrar imágenes y mapas
- **Streaming**: Respuestas en tiempo real
- **Personalization**: Perfiles de usuario persistentes
- **Multi-language**: Expandir más allá del español

---

**Esta arquitectura transforma el PoC actual en un sistema productivo manteniendo la compatibilidad con el código existente mientras añade capacidades de IA conversacional avanzadas.**
