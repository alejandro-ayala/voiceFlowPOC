# Quick Start - VoiceFlow Tourism PoC

**Actualizado**: 12 de Febrero de 2026

---

## Setup en 5 minutos

### 1. Instalar dependencias

```bash
# Requiere Python 3.11+ y Poetry (https://python-poetry.org/docs/#installation)
poetry install
```

### 2. Configurar credenciales

```bash
cp .env.example .env
# Editar .env con tus credenciales:
# AZURE_SPEECH_KEY=tu_key
# AZURE_SPEECH_REGION=tu_region
# OPENAI_API_KEY=tu_key (solo si use_real_agents=true)
```

### 3. Ejecutar la aplicacion

```bash
# Con Docker (recomendado)
docker compose up --build

# Sin Docker
poetry run python presentation/server_launcher.py
```

Acceder a:
- **Aplicacion**: http://localhost:8000
- **API Docs** (Swagger): http://localhost:8000/api/docs
- **Health check**: http://localhost:8000/api/v1/health/

### 4. Modo demo (sin API keys)

Si no tienes credenciales de Azure u OpenAI, la aplicacion funciona en modo simulacion:

```bash
# Editar .env
VOICEFLOW_USE_REAL_AGENTS=false
```

El chat respondera con respuestas hardcodeadas sobre turismo accesible en Madrid y la transcripcion de audio retornara texto simulado.

## Arquitectura

```
Browser (index.html)
    |
    +-- Audio: POST /api/v1/audio/transcribe
    |       +-- AudioService -> STTFactory -> Azure/Whisper/Simulacion
    |
    +-- Chat: POST /api/v1/chat/message
            +-- LocalBackendAdapter -> TourismMultiAgent (LangChain + GPT-4)
                    +-- TourismNLUTool
                    +-- AccessibilityAnalysisTool
                    +-- RoutePlanningTool
                    +-- TourismInfoTool
```

## Archivos clave

| Archivo | Descripcion |
|---------|-------------|
| `presentation/server_launcher.py` | Entry point principal |
| `presentation/fastapi_factory.py` | Fabrica FastAPI (create_application) |
| `application/api/v1/` | Endpoints REST (health, audio, chat) |
| `application/orchestration/backend_adapter.py` | Adapter a business layer |
| `business/ai_agents/langchain_agents.py` | Multi-agent LangChain |
| `integration/configuration/settings.py` | Configuracion centralizada |
| `integration/external_apis/stt_factory.py` | Factory de servicios STT |
| `.env` | Variables de entorno (credenciales) |

## Verificar que todo funciona

```bash
# Health check
curl http://localhost:8000/api/v1/health/

# Enviar mensaje de chat
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Como llego al Museo del Prado en silla de ruedas?"}'

# Respuestas demo
curl http://localhost:8000/api/v1/chat/demo/responses
```

## Problemas comunes

### Import errors
```bash
# Verificar que las dependencias estan instaladas
poetry run python -c "from presentation.fastapi_factory import app; print('OK')"
```

### Azure no conecta
- Verificar que `.env` tiene `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION` correctos
- Probar con `VOICEFLOW_USE_REAL_AGENTS=false` para modo simulacion

### Puerto ocupado
```bash
poetry run python presentation/server_launcher.py --port 9000
```

## Documentacion

- [DEVELOPMENT.md](DEVELOPMENT.md) - Guia completa de desarrollo
- [AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md) - Configuracion de Azure Speech
- [ROADMAP.md](ROADMAP.md) - Plan de evolucion del proyecto
- [design/](design/) - Documentos de diseno por capa
