# Arquitectura Multi-Agente: LangChain + STT

**Actualizado**: 23 de Febrero de 2026
**Version**: 4.2 - Pipeline con LocationNER + contrato de salida NER

---

## ⚠️ ESTADO ACTUAL: Tools con Mock Data (STUBS) + NER funcional

**IMPORTANTE:** Las herramientas (tools) actuales son **prototipos con datos hardcodeados**, excepto la extracción NER de localizaciones:
- ❌ **NLU Tool**: Regex + diccionario de ~10 venues de Madrid
- ✅ **LocationNER Tool**: extracción real de localizaciones con spaCy (si modelo disponible)
- ❌ **Accessibility Tool**: Lookup en base de datos simulada (4 venues)
- ❌ **Route Tool**: Rutas predefinidas, no consultan APIs reales
- ❌ **Tourism Info Tool**: Horarios/precios son MOCK DATA

**Impacto:**
- Las tools NO aportan datos reales, el LLM usa su conocimiento pre-entrenado
- Solo funciona para casos hardcodeados (Madrid + ~10 venues)
- NO escala a otras ciudades sin añadir más mock data

**Siguiente paso:** Ver [ESTADO_ACTUAL_SISTEMA.md](./ESTADO_ACTUAL_SISTEMA.md) y [REFACTOR_PLAN_PROFILE_DRIVEN_RESPONSES.md](./REFACTOR_PLAN_PROFILE_DRIVEN_RESPONSES.md) (Fase 0) para plan de integración con APIs reales.

---

## Contexto

El sistema VoiceFlow Tourism PoC combina Speech-to-Text (STT) con un sistema multi-agente LangChain para proporcionar asistencia de turismo accesible en Madrid. El usuario habla en español, el sistema transcribe y procesa la consulta a través de agentes especializados que generan recomendaciones de accesibilidad.

## Flujo de datos

```
 Usuario (voz en espanol)
         |
         v
  +-----------------+     Presentation Layer
  | Browser (UI)    |     presentation/templates/index.html
  | AudioHandler.js |     presentation/static/js/audio.js
  +-----------------+
         |
         | POST /api/v1/audio/transcribe (WebM audio)
         v
  +-------------------+   Application Layer
  | audio.py endpoint |   application/api/v1/audio.py
  +-------------------+
         |
         | Depends(get_audio_processor)
         v
  +-------------------+   Application Layer
  | AudioService      |   application/services/audio_service.py
  +-------------------+
         |
         | _get_stt_agent() -> lazy init
         v
  +-------------------+   Integration Layer
  | VoiceflowSTTAgent |   integration/external_apis/stt_agent.py
  +-------------------+
         |
         | STTServiceFactory.create_from_config()
         v
  +-------------------+   Integration Layer
  | STTServiceFactory |   integration/external_apis/stt_factory.py
  +---------+---------+
            |
    +-------+-------+-------+
    |               |               |
    v               v               v
 Azure STT    Whisper Local   Whisper API
 (produccion) (offline)       (cloud)

         === Transcripcion completada ===

         | Texto transcrito
         v
  +-------------------+   Presentation Layer (UI)
  | ChatHandler.js    |   El usuario puede editar o enviar directamente
  +-------------------+
         |
         | POST /api/v1/chat/message
         v
  +-------------------+   Application Layer
  | chat.py endpoint  |   application/api/v1/chat.py
  +-------------------+
         |
         | Depends(get_backend_adapter)
         v
  +----------------------+   Application Layer
  | LocalBackendAdapter  |   application/orchestration/backend_adapter.py
  +----------------------+
         |
         | use_real_agents?
         |
    +----+----+
    |         |
    v         v
  REAL      SIMULADO
    |         |
    v         |
  +----------------------------------+   Business Layer (core/)
  | MultiAgentOrchestrator           |   business/core/orchestrator.py
  |   process_request() → AgentResponse
  +----------------------------------+
    |
    v (Template Method)
  +----------------------------------+   Business Layer (domains/tourism/)
  | TourismMultiAgent                |   business/domains/tourism/agent.py
  |   _execute_pipeline()            |
  +----------------------------------+
    |
       | Ejecuta 5 tools secuencialmente
    |
    +---> TourismNLUTool             (tools/nlu_tool.py)
       +---> LocationNERTool            (tools/location_ner_tool.py)
    +---> AccessibilityAnalysisTool  (tools/accessibility_tool.py)
    +---> RoutePlanningTool          (tools/route_planning_tool.py)
    +---> TourismInfoTool            (tools/tourism_info_tool.py)
    |
    | _build_response_prompt()       (prompts/response_prompt.py)
    v
  +-------------------+
  | ChatOpenAI GPT-4  |   Genera respuesta conversacional en espanol
  +-------------------+
         |
         v
  Respuesta JSON al frontend
```

## Componentes del sistema multi-agente

### Orquestador: `TourismMultiAgent`

**Ubicacion**: `business/domains/tourism/agent.py`
**Hereda de**: `business/core/orchestrator.py` → `MultiAgentOrchestrator`
**LLM**: ChatOpenAI GPT-4 (temperature=0.3, max_tokens=1500)

El orquestador extiende `MultiAgentOrchestrator` (patron Template Method) e implementa `_execute_pipeline()` que ejecuta 5 tools en secuencia. El algoritmo base (invoke LLM, gestionar historial, retornar `AgentResponse`) esta en `core/`.

```python
class TourismMultiAgent(MultiAgentOrchestrator):
    def __init__(self, openai_api_key=None):
        llm = ChatOpenAI(model="gpt-4", temperature=0.3, max_tokens=1500)
        super().__init__(llm=llm, system_prompt=SYSTEM_PROMPT)
        self.nlu = TourismNLUTool()
              self.location_ner = LocationNERTool()
        self.accessibility = AccessibilityAnalysisTool()
        self.route = RoutePlanningTool()
        self.tourism_info = TourismInfoTool()

       def _execute_pipeline(self, user_input: str, profile_context=None) -> tuple[dict[str, str], dict]:
        nlu_result = self.nlu._run(user_input)
              location_ner_result = self.location_ner._run(user_input)
        accessibility_result = self.accessibility._run(nlu_result)
        route_result = self.route._run(accessibility_result)
        tourism_result = self.tourism_info._run(nlu_result)
              tool_results = {
                     "nlu": nlu_result,
                     "locationner": location_ner_result,
                     "accessibility": accessibility_result,
                     "route": route_result,
                     "tourism_info": tourism_result,
              }
              metadata = {"pipeline_steps": [...], "tool_results_parsed": {...}}
              return tool_results, metadata
```

### Tools especializados

| Tool | Clase | Input | Output |
|------|-------|-------|--------|
| NLU | `TourismNLUTool` | Texto del usuario | Intent, entities, accessibility type |
| Location NER | `LocationNERTool` | Texto del usuario (crudo) | `locations`, `top_location`, `provider`, `model`, `status` |
| Accesibilidad | `AccessibilityAnalysisTool` | Resultado NLU (JSON) | Score, facilities, certification |
| Rutas | `RoutePlanningTool` | Resultado accesibilidad (JSON) | Rutas metro/bus, costes, pasos |
| Info turistica | `TourismInfoTool` | Resultado NLU (JSON) | Horarios, precios, servicios |

Todos los tools extienden `langchain.tools.BaseTool` e implementan `_run()` (sync) y `_arun()` (async, delegado a sync).

### Datos estaticos

Los datos de Madrid estan separados en modulos independientes dentro de `business/domains/tourism/data/`:

| Modulo | Contenido |
|--------|-----------|
| `nlu_patterns.py` | Patrones de intent, destino, accesibilidad, keywords Madrid |
| `accessibility_data.py` | `ACCESSIBILITY_DB` - scores, facilities, certificaciones por venue |
| `route_data.py` | `ROUTE_DB` - rutas metro/bus, costes, pasos por destino |
| `venue_data.py` | `VENUE_DB` - horarios, precios, servicios por venue |

**Venues**: Museo del Prado, Reina Sofia, espacios musicales, restaurantes.
**Accesibilidad**: Scores, facilities (rampas, banos, audioguias), certificaciones (ONCE).
**Rutas**: Metro (lineas 1, 2), bus (linea 27), costes (1.50-2.50 EUR).

## Decisiones arquitectonicas

### STT como servicio independiente (no como agente LangChain)

El STT es infraestructura, no logica de negocio:
- Menor latencia (sin overhead de LLM para audio)
- Control directo sobre el audio (formatos, sample rate, conversion)
- Fallback chain independiente (Azure -> Whisper -> simulacion)
- Testeable sin API keys de OpenAI

### Orquestacion secuencial (no paralela)

Actualmente los tools se ejecutan en secuencia fija porque cada tool recibe el output del anterior. Esto es una limitacion conocida; la Fase 1 del ROADMAP propone orquestacion selectiva basada en intent.

### Modo simulacion en el adapter

`LocalBackendAdapter._simulate_ai_response()` contiene ~110 lineas de respuestas hardcodeadas que permiten desarrollar y demostrar el frontend sin consumir creditos de OpenAI. Este codigo deberia moverse a un mock service separado.

## Ejemplo de interaccion

**Input**: "Necesito una ruta accesible al Museo del Prado para silla de ruedas"

1. **NLU Tool** detecta:
   - Intent: `route_planning`
   - Destination: `Museo del Prado`
   - Accessibility: `wheelchair`

2. **LocationNER Tool** extrae:
       - Locations: `["Museo del Prado", "Madrid"]`
       - Top location: `Museo del Prado`

3. **Accessibility Tool** retorna:
   - Score: 9.2/10
   - Facilities: rampas, banos adaptados, audioguias, caminos tactiles
   - Certification: ONCE

4. **Route Tool** retorna:
   - Metro Linea 2 hasta Banco de Espana (25 min, accesible)
   - Bus 27 hasta Cibeles (35 min, piso bajo)

5. **Tourism Tool** retorna:
   - Horario: 10:00-20:00 (L-S), 10:00-19:00 (Dom)
   - Precio: 15 EUR (gratis para visitantes con discapacidad + acompanante)
   - Contacto accesibilidad: +34 91 330 2800

6. **GPT-4** combina todo en respuesta conversacional en espanol.

## Documentacion relacionada

- [03_business_layer_design.md](design/03_business_layer_design.md) - SDD detallado de business layer (actualizado post-Fase 2B)
- [04_application_layer_design.md](design/04_application_layer_design.md) - SDD del adapter y servicios
- [02_integration_layer_design.md](design/02_integration_layer_design.md) - SDD del pipeline STT
- [ROADMAP.md](ROADMAP.md) - Plan de evolucion del proyecto
- [PROPOSAL_FASE_2B.md](PROPOSAL_FASE_2B.md) - Propuesta y SDD de la descomposicion
