# VoiceFlow PoC - Turismo Accesible con STT + Multi-Agent Pipeline

PoC de asistente de turismo accesible con entrada por voz y pipeline multi-tool sobre LangChain.

## Estado actual (Feb 2026)

- STT real con Azure Speech Services funcionando.
- Pipeline de tools en dominio turismo funcionando.
- `LocationNER` integrado y expuesto en salida API.
- Varias tools de dominio siguen en modo stub/mock (gap conocido POC→producción).

## Pipeline actual

`Audio/UI -> Azure STT -> Chat API -> NLU -> LocationNER -> Accessibility -> Routes -> Venue Info -> LLM Synthesis`

### Salida NER en API

La respuesta de `POST /api/v1/chat/message` incluye:

- `entities.location_ner`
- `metadata.tool_outputs.location_ner`

Con shape típico:

```json
{
  "status": "ok",
  "locations": ["Barcelona"],
  "top_location": "Barcelona",
  "provider": "spacy",
  "model": "es_core_news_md",
  "language": "es"
}
```

## Inicio rápido

### Opción recomendada (Docker)

```bash
cd /home/alex/Documentos/Code/voiceFlowPOC
docker compose up --build
```

- UI: `http://localhost:8000`
- API docs: `http://localhost:8000/api/docs`

### Opción local (Poetry)

```bash
cd /home/alex/Documentos/Code/voiceFlowPOC
poetry install
poetry run python presentation/server_launcher.py
```

## Verificación rápida de NER

```bash
curl -s -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message":"Turismo cultural en el centro de Barcelona"}' \
| jq '{entities: .entities.location_ner, ner: .metadata.tool_outputs.location_ner}'
```

## Estructura de capas

- `presentation/`: UI web y factory FastAPI
- `application/`: endpoints API, servicios y backend adapter
- `business/`: orquestador y tools por dominio
- `integration/`: STT, NER providers/factories y configuración
- `shared/`: interfaces, excepciones y DI

## Documentación clave

- `documentation/API_REFERENCE.md`
- `documentation/ARCHITECTURE_MULTIAGENT.md`
- `documentation/ARCHITECTURE_VOICE-FLOW-POC.md`
- `documentation/ESTADO_ACTUAL_SISTEMA.md`
- `documentation/PLAN_IMPLEMENTACION_NER_5_COMMITS.md`
- `documentation/DEVELOPMENT.md`

## Nota de alcance

Esta iteración cierra integración de `LocationNER` en pipeline y contrato API.
No implica productización de todas las tools de dominio (stubs documentados).
