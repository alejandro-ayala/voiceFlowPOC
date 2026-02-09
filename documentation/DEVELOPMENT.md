# Guia de Desarrollo - VoiceFlow Tourism PoC

**Actualizado**: 11 de Febrero de 2026
**Arquitectura**: 4 capas (shared, integration, business, application) + presentation + CI/CD Pipeline

---

## Prerrequisitos

- Python 3.9+
- Git
- Editor con soporte para type hints (VS Code recomendado)
- ffmpeg (para conversion de audio webm/mp3)

## Setup inicial

1. **Clonar y navegar al proyecto:**
   ```bash
   git clone <repo-url>
   cd voiceFlowPOC-refactor-baseline
   ```

2. **Crear entorno virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate       # Linux/Mac
   # venv\Scripts\activate        # Windows
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt -r requirements-ui.txt
   ```

4. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales (Azure Speech, OpenAI)
   ```

5. **Ejecutar la aplicacion con Docker (recomendado):**
   ```bash
   docker compose up --build
   # Acceder a http://localhost:8000
   # API docs en http://localhost:8000/api/docs (modo debug)
   # Hot-reload automatico al editar archivos
   ```
   
   **Alternativa local (sin Docker):**
   ```bash
   python presentation/server_launcher.py
   # Acceder a http://localhost:8000
   # API docs en http://localhost:8000/api/docs (modo debug)
   ```

## Estructura del proyecto

```
voiceFlowPOC-refactor-baseline/
├── shared/                          # Contratos e infraestructura transversal
│   ├── interfaces/
│   │   ├── interfaces.py            #   AudioProcessorInterface, BackendInterface, ConversationInterface
│   │   └── stt_interface.py         #   STTServiceInterface + excepciones STT
│   ├── exceptions/
│   │   └── exceptions.py            #   VoiceFlowException hierarchy + HTTP mapping
│   └── utils/
│       └── dependencies.py          #   Composition root (FastAPI DI)
│
├── integration/                     # Integraciones externas y configuracion
│   ├── configuration/
│   │   └── settings.py              #   Settings (Pydantic BaseSettings, prefijo VOICEFLOW_)
│   ├── external_apis/
│   │   ├── azure_stt_client.py      #   AzureSpeechService (STTServiceInterface)
│   │   ├── whisper_services.py      #   WhisperLocalService, WhisperAPIService
│   │   ├── stt_factory.py           #   STTServiceFactory (patron Factory)
│   │   └── stt_agent.py             #   VoiceflowSTTAgent + create_stt_agent()
│   └── data_persistence/
│       └── conversation_repository.py  # ConversationService (in-memory)
│
├── business/                        # Logica de negocio (LangChain agents)
│   └── ai_agents/
│       └── langchain_agents.py      #   TourismMultiAgent + 4 LangChain tools
│
├── application/                     # API REST, servicios, orquestacion
│   ├── api/v1/
│   │   ├── health.py                #   GET /api/v1/health/*
│   │   ├── audio.py                 #   POST /api/v1/audio/transcribe, validate, etc.
│   │   └── chat.py                  #   POST /api/v1/chat/message, conversations, etc.
│   ├── services/
│   │   ├── audio_service.py         #   AudioService (AudioProcessorInterface)
│   │   └── conversation_service.py  #   ConversationService (copia de integration/)
│   ├── orchestration/
│   │   └── backend_adapter.py       #   LocalBackendAdapter (BackendInterface)
│   └── models/
│       ├── requests.py              #   Pydantic request models
│       └── responses.py             #   Pydantic response models
│
├── presentation/                    # UI, servidor, recursos estaticos
│   ├── fastapi_factory.py           #   create_application(), lifespan, exception handlers
│   ├── server_launcher.py           #   Script de arranque alternativo
│   ├── templates/
│   │   └── index.html               #   Plantilla Jinja2 (Bootstrap 5)
│   └── static/
│       ├── css/app.css              #   Estilos custom
│       └── js/
│           ├── app.js               #   Coordinador (VoiceFlowApp)
│           ├── audio.js             #   AudioHandler (grabacion, visualizacion)
│           └── chat.js              #   ChatHandler (mensajes, conversaciones)
│
├── tests/                           # Tests (estructura preparada)
│   ├── conftest.py
│   ├── test_shared/
│   ├── test_application/
│   ├── test_integration/
│   └── test_business/
│
├── documentation/                   # Documentacion del proyecto
│   └── design/                      #   SDDs por capa (01-05)
│
├── presentation/
│   ├── server_launcher.py           # Entry point principal
├── requirements.txt                 # Dependencias core (Azure, LangChain, audio)
├── requirements-ui.txt              # Dependencias web (FastAPI, uvicorn, etc.)
├── .env.example                     # Template de configuracion
└── INFORME_FINAL_ARQUITECTONICO.md  # Documento de arquitectura general
```

## Comandos de desarrollo

### Ejecutar la aplicacion

```bash
# Modo desarrollo (con hot-reload si DEBUG=true en .env)
python presentation/server_launcher.py

# Especificar host y puerto
python presentation/server_launcher.py --host 0.0.0.0 --port 9000

# Modo simulacion (sin API keys de OpenAI)
# Editar .env: VOICEFLOW_USE_REAL_AGENTS=false
python presentation/server_launcher.py
```

### Verificar imports por capa

```bash
# Shared (sin dependencias internas)
python -c "from shared.interfaces.interfaces import BackendInterface; print('OK')"
python -c "from shared.exceptions.exceptions import VoiceFlowException; print('OK')"

# Integration (depende de shared)
python -c "from integration.configuration.settings import Settings; print('OK')"
python -c "from integration.external_apis.stt_factory import STTServiceFactory; print('OK')"

# Business (depende de librerias externas)
python -c "from business.ai_agents.langchain_agents import TourismMultiAgent; print('OK')"

# Application (depende de shared, integration, business)
python -c "from application.services.audio_service import AudioService; print('OK')"
python -c "from application.orchestration.backend_adapter import LocalBackendAdapter; print('OK')"

# Presentation (depende de todo)
python -c "from presentation.fastapi_factory import create_application; print('OK')"
```

### Verificaciones de Linting y Formato (CI/CD Local)

**Antes de hacer push**, ejecuta las mismas verificaciones que el CI/CD pipeline:

#### 1. **Instalar herramientas de linting**

```bash
# Instalar ruff (linter y formatter) y mypy (type checker)
pip install ruff mypy

# Nota: Asegúrate de instalar en el venv del proyecto, no global
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows
```

#### 2. **Ejecutar verificaciones**

```bash
# Check linting (detectar errores de estilo, imports no usados, etc.)
ruff check .

# Check de formato (verificar que el código siga el estándar)
ruff format --check .

# Type checking (información sobre tipos - no bloquea, solo informativo)
mypy application/ business/ shared/ integration/ presentation/ --ignore-missing-imports --no-error-summary
```

#### 3. **Auto-fix automático**

Si hay errores, ruff puede arreglar muchos automáticamente:

```bash
# Auto-fix errores que se pueden arreglar automáticamente
ruff check . --fix

# Auto-format todo el código al estándar
ruff format .

# Luego verifica que todo pasó
ruff check . && ruff format --check .
```

#### 4. **Errores comunes** que mira ruff:

- **E722**: `except:` sin especificar excepción → `except Exception:`
- **F401**: Imports no usados → remover o agregar a `__all__`
- **F841**: Variables asignadas pero no usadas → remover
- **F811**: Función redefinida → remover duplicada
- **E501**: Línea muy larga → dividir o reformatear
- **Formato**: Indentación, espacios, saltos de línea inconsistentes

#### 5. **Flujo antes de hacer commit/push**

```bash
# 1. Verificar que el código pasa linting
ruff check .

# 2. Si hay errores, auto-fixear
ruff check . --fix
ruff format .

# 3. Verificar de nuevo
ruff check . && ruff format --check .

# 4. Si todo pasa, hacer commit
git add -A
git commit -m "fix: linting and format issues"
git push
```

#### 6. **CI/CD Pipeline Automático**

El proyecto tiene un pipeline en `.github/workflows/ci.yml` que:
- ✅ Ejecuta `ruff check .` en cada push/PR
- ✅ Ejecuta `ruff format --check .` en cada push/PR
- ✅ Ejecuta `mypy` (informativo, no bloquea)
- ✅ Construye Docker image
- ✅ Valida health checks

Si alguna verificación falla localmente, fallará también en el CI/CD y bloqueará el merge.

---

### Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Tests por capa
pytest tests/test_shared/ -v
pytest tests/test_business/ -v
pytest tests/test_application/ -v

# Con coverage
pytest tests/ --cov=shared --cov=integration --cov=business --cov=application --cov=presentation --cov-report=html
```

### Verificar servicio STT

```bash
python -c "
from integration.external_apis.stt_factory import STTServiceFactory
services = STTServiceFactory.get_available_services()
print(f'Servicios disponibles: {services}')
"
```

## Agregar un nuevo servicio STT

**Paso 1: Implementar la interfaz** en `integration/external_apis/`:

```python
# integration/external_apis/nuevo_stt_service.py
from shared.interfaces.stt_interface import STTServiceInterface

class NuevoSTTService(STTServiceInterface):
    async def transcribe_audio(self, audio_path, **kwargs) -> str:
        # Implementacion
        pass

    def is_service_available(self) -> bool:
        pass

    def get_supported_formats(self) -> list[str]:
        return ["wav", "mp3"]

    def get_service_info(self) -> dict:
        return {"service_name": "NuevoSTT", "available": True}
```

**Paso 2: Registrar en Factory** (`integration/external_apis/stt_factory.py`):

```python
STTServiceFactory.register_service("nuevo_stt", NuevoSTTService)
```

**Paso 3: Actualizar `.env.example`** con las variables de configuracion necesarias.

## Agregar un nuevo endpoint API

1. Crear o editar el router en `application/api/v1/`
2. Definir request/response models en `application/models/`
3. Si necesita nueva logica de negocio, crear servicio en `application/services/`
4. Registrar el router en `presentation/fastapi_factory.py`:
   ```python
   app.include_router(nuevo_router, prefix="/api/v1", tags=["nuevo"])
   ```

## Variables de entorno

Todas las variables de la aplicacion usan el prefijo `VOICEFLOW_` (gestionado por Pydantic BaseSettings):

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `VOICEFLOW_DEBUG` | `true` | Modo debug (habilita /api/docs) |
| `VOICEFLOW_HOST` | `localhost` | Host del servidor |
| `VOICEFLOW_PORT` | `8000` | Puerto del servidor |
| `VOICEFLOW_USE_REAL_AGENTS` | `true` | Usar LangChain real o simulacion |
| `VOICEFLOW_LOG_LEVEL` | `INFO` | Nivel de logging |

Secretos de servicios externos (sin prefijo):

| Variable | Descripcion |
|----------|-------------|
| `AZURE_SPEECH_KEY` | API key de Azure Speech Services |
| `AZURE_SPEECH_REGION` | Region de Azure (ej: `westeurope`) |
| `OPENAI_API_KEY` | API key de OpenAI (para LangChain GPT-4) |
| `STT_SERVICE` | Servicio STT: `azure`, `whisper_local`, `whisper_api` |

## Convenciones de codigo

- **Type hints** en todas las firmas de funciones
- **Async/await** para operaciones I/O
- **Imports absolutos** desde la raiz del proyecto (nunca relativos entre capas)
- **Interfaces en shared/**: Toda comunicacion entre capas pasa por interfaces abstractas
- **Sin imports circulares**: Las dependencias van bottom-up (shared <- integration <- business <- application <- presentation)

## Documentacion de referencia

- [SDDs por capa](design/) - Documentos de diseno detallados (01-05)
- [ROADMAP.md](ROADMAP.md) - Plan de evolucion del proyecto
- [INFORME_FINAL_ARQUITECTONICO.md](../INFORME_FINAL_ARQUITECTONICO.md) - Estado general de la arquitectura
- [AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md) - Configuracion de Azure Speech Services
