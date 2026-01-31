# Arquitectura Multi-Agente: LangChain + STT

**Actualizado**: 4 de Febrero de 2026
**Version**: 3.0 - Arquitectura 4 capas

---

## Contexto

El sistema VoiceFlow Tourism PoC combina Speech-to-Text (STT) con un sistema multi-agente LangChain para proporcionar asistencia de turismo accesible en Madrid. El usuario habla en espanol, el sistema transcribe y procesa la consulta a traves de agentes especializados que generan recomendaciones de accesibilidad.

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
  +------------------------+   Business Layer
  | TourismMultiAgent      |   business/ai_agents/langchain_agents.py
  +------------------------+
    |
    | Ejecuta 4 tools secuencialmente
    |
    +---> TourismNLUTool         (intent + entities + accessibility)
    +---> AccessibilityAnalysisTool  (score, facilities, certification)
    +---> RoutePlanningTool      (rutas metro/bus, costes)
    +---> TourismInfoTool        (horarios, precios, servicios)
    |
    | Combina resultados en prompt final
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

**Ubicacion**: `business/ai_agents/langchain_agents.py`
**LLM**: ChatOpenAI GPT-4 (temperature=0.3, max_tokens=1500)

El orquestador ejecuta los 4 tools en secuencia fija y luego pasa todos los resultados como contexto a GPT-4 para generar la respuesta final en espanol.

```python
class TourismMultiAgent:
    def __init__(self, openai_api_key=None):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.3)
        self.tools = [TourismNLUTool(), AccessibilityAnalysisTool(),
                      RoutePlanningTool(), TourismInfoTool()]
        self.conversation_history = []

    async def process_request(self, user_input: str) -> str:
        nlu = TourismNLUTool()._run(user_input)
        accessibility = AccessibilityAnalysisTool()._run(nlu)
        routes = RoutePlanningTool()._run(accessibility)
        tourism = TourismInfoTool()._run(nlu)
        # Combina todo en prompt -> GPT-4 -> respuesta
```

### Tools especializados

| Tool | Clase | Input | Output |
|------|-------|-------|--------|
| NLU | `TourismNLUTool` | Texto del usuario | Intent, entities, accessibility type |
| Accesibilidad | `AccessibilityAnalysisTool` | Resultado NLU (JSON) | Score, facilities, certification |
| Rutas | `RoutePlanningTool` | Resultado accesibilidad (JSON) | Rutas metro/bus, costes, pasos |
| Info turistica | `TourismInfoTool` | Resultado NLU (JSON) | Horarios, precios, servicios |

Todos los tools extienden `langchain.tools.BaseTool` e implementan `_run()` (sync) y `_arun()` (async, delegado a sync).

### Datos estaticos

Los tools contienen datos hardcodeados sobre Madrid:

- **Venues**: Museo del Prado, Reina Sofia, Thyssen, Retiro, Palacio Real, Templo de Debod
- **Accesibilidad**: Scores, facilities (rampas, banos, audioguias), certificaciones (ONCE)
- **Rutas**: Metro (lineas 1, 2), bus (linea 27), costes (1.50-2.50 EUR)
- **Info**: Horarios, precios, exposiciones, contactos de accesibilidad

Estos datos deberan extraerse a modulos separados en la Fase 1 del [ROADMAP](ROADMAP.md).

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

`LocalBackendAdapter._simulate_ai_response()` contiene ~110 lineas de respuestas hardcodeadas que permiten desarrollar y demostrar el frontend sin consumir creditos de OpenAI. Este codigo deberia moverse a un mock service separado (ver ROADMAP Fase 1).

## Ejemplo de interaccion

**Input**: "Necesito una ruta accesible al Museo del Prado para silla de ruedas"

1. **NLU Tool** detecta:
   - Intent: `route_planning`
   - Destination: `Museo del Prado`
   - Accessibility: `wheelchair`

2. **Accessibility Tool** retorna:
   - Score: 9.2/10
   - Facilities: rampas, banos adaptados, audioguias, caminos tactiles
   - Certification: ONCE

3. **Route Tool** retorna:
   - Metro Linea 2 hasta Banco de Espana (25 min, accesible)
   - Bus 27 hasta Cibeles (35 min, piso bajo)

4. **Tourism Tool** retorna:
   - Horario: 10:00-20:00 (L-S), 10:00-19:00 (Dom)
   - Precio: 15 EUR (gratis para visitantes con discapacidad + acompanante)
   - Contacto accesibilidad: +34 91 330 2800

5. **GPT-4** combina todo en respuesta conversacional en espanol.

## Documentacion relacionada

- [03_business_layer_design.md](design/03_business_layer_design.md) - SDD detallado de business layer
- [04_application_layer_design.md](design/04_application_layer_design.md) - SDD del adapter y servicios
- [02_integration_layer_design.md](design/02_integration_layer_design.md) - SDD del pipeline STT
- [ROADMAP.md](ROADMAP.md) - Fase 1: descomposicion del monolito multi-agente
