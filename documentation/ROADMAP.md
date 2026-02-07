# ROADMAP: VoiceFlow Tourism PoC

**Fecha**: 4 de Febrero de 2026
**Estado actual**: Arquitectura 4 capas implementada, monolito business pendiente de descomposición
**Versión actual del proyecto**: 1.0.0

---

## Visión general

Este roadmap define las fases de evolución del proyecto desde su estado actual (PoC funcional con arquitectura limpia en 4 capas) hasta un sistema desplegable, testeable y mantenible. Las fases están ordenadas por prioridad y dependencia.

```
Fase 1 ─ Descomposición de langchain_agents.py (business layer)
  │
Fase 2 ─ Dockerización de la arquitectura
  │
Fase 3 ─ Suite de testing
  │
Fase 4 ─ Persistencia real (base de datos)
  │
Fase 5 ─ Observabilidad y monitoring
  │
Fase 6 ─ Seguridad y autenticación
  │
Fase 7 ─ CI/CD pipeline
```

---

## Fase 1: Descomposición de `langchain_agents.py`

### 1.1 Contexto y problema

El archivo `business/ai_agents/langchain_agents.py` es un monolito de 580 líneas que contiene:

- 4 clases de herramientas LangChain (`TourismNLUTool`, `AccessibilityAnalysisTool`, `RoutePlanningTool`, `TourismInfoTool`)
- 1 clase orquestadora (`TourismMultiAgent`)
- 2 funciones de test (`test_individual_tools`, `test_orchestrator`)
- Datos hardcodeados de accesibilidad, rutas y venues mezclados con la lógica
- Bloque `if __name__` con lógica de ejecución

Problemas concretos:

1. **SRP violado**: Cada tool mezcla lógica de parsing, lógica de negocio y datos estáticos en el mismo método `_run()`
2. **Datos acoplados a lógica**: Los diccionarios `accessibility_db`, `route_db`, `venue_db` (~200 líneas de datos) están inline dentro de los métodos
3. **Sin interfaz formal**: `TourismMultiAgent` no implementa ninguna interfaz de `shared/interfaces/`; el adapter usa `hasattr()` con 5 fallbacks para encontrar un método compatible
4. **Orquestación secuencial fija**: `process_request()` ejecuta siempre los 4 tools en orden, sin importar la intención del usuario
5. **Tests en código de producción**: `test_individual_tools()` y `test_orchestrator()` no pertenecen al módulo
6. **Prompts hardcodeados**: El system prompt y el final prompt están embebidos como strings multilínea dentro de métodos

### 1.2 Arquitectura objetivo

```
business/
├── __init__.py
├── ai_agents/
│   ├── __init__.py                      # Re-exports: TourismMultiAgent
│   ├── orchestrator.py                  # TourismMultiAgent (orquestador)
│   └── tools/
│       ├── __init__.py                  # Re-exports: todas las tools
│       ├── base.py                      # TourismBaseTool (si se necesita lógica común)
│       ├── nlu_tool.py                  # TourismNLUTool
│       ├── accessibility_tool.py        # AccessibilityAnalysisTool
│       ├── route_planning_tool.py       # RoutePlanningTool
│       └── tourism_info_tool.py         # TourismInfoTool
├── data/
│   ├── __init__.py
│   ├── accessibility_data.py            # ACCESSIBILITY_DB dict
│   ├── route_data.py                    # ROUTE_DB dict
│   ├── venue_data.py                    # VENUE_DB dict
│   └── nlu_patterns.py                 # INTENT_PATTERNS, DESTINATION_PATTERNS, ACCESSIBILITY_PATTERNS
├── prompts/
│   ├── __init__.py
│   ├── system_prompt.py                 # SYSTEM_PROMPT constant
│   └── response_prompt.py              # RESPONSE_PROMPT_TEMPLATE (con placeholders)
└── domain/
    ├── __init__.py
    └── models.py                        # NLUResult, AccessibilityInfo, RouteInfo, VenueInfo (dataclasses)
```

### 1.3 Nuevas interfaces en `shared/`

Añadir a `shared/interfaces/interfaces.py`:

```python
class TourismAgentInterface(ABC):
    """Contrato para el agente de turismo accesible."""

    @abstractmethod
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Procesa una consulta de turismo y retorna respuesta estructurada."""
        pass

    @abstractmethod
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Retorna el historial de conversación."""
        pass

    @abstractmethod
    def clear_conversation(self) -> None:
        """Limpia el historial de conversación."""
        pass
```

El return type de `process_request` debe ser un dict con estructura definida:

```python
{
    "response_text": str,          # Respuesta en lenguaje natural
    "nlu_result": {                # Resultado del análisis NLU
        "intent": str,
        "entities": dict,
        "confidence": float
    },
    "accessibility_info": dict,    # Info de accesibilidad (opcional)
    "route_info": dict,            # Info de rutas (opcional)
    "venue_info": dict             # Info del venue (opcional)
}
```

### 1.4 Modelos de dominio

Crear `business/domain/models.py`:

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class TourismIntent(str, Enum):
    INFORMATION_REQUEST = "information_request"
    ROUTE_PLANNING = "route_planning"
    EVENT_SEARCH = "event_search"
    RESTAURANT_SEARCH = "restaurant_search"
    ACCOMMODATION_SEARCH = "accommodation_search"

class AccessibilityType(str, Enum):
    GENERAL = "general"
    WHEELCHAIR = "wheelchair"
    VISUAL_IMPAIRMENT = "visual_impairment"
    HEARING_IMPAIRMENT = "hearing_impairment"

@dataclass
class NLUResult:
    intent: TourismIntent
    destination: str
    accessibility_type: AccessibilityType
    confidence: float
    raw_input: str

@dataclass
class AccessibilityInfo:
    level: str
    score: float
    facilities: List[str]
    certification: str
    warnings: List[str] = field(default_factory=list)

@dataclass
class RouteOption:
    route_id: str
    transport: str
    duration: str
    accessibility: str
    steps: List[str]
    features: List[str]

@dataclass
class RouteInfo:
    routes: List[RouteOption]
    alternatives: List[str]
    estimated_cost: str

@dataclass
class VenueInfo:
    name: str
    opening_hours: Dict[str, str]
    pricing: Dict[str, str]
    accessibility_reviews: List[str]
    accessibility_services: Dict[str, str]
    contact: Dict[str, str]

@dataclass
class AgentResponse:
    response_text: str
    nlu_result: Optional[NLUResult] = None
    accessibility_info: Optional[AccessibilityInfo] = None
    route_info: Optional[RouteInfo] = None
    venue_info: Optional[VenueInfo] = None
```

### 1.5 Extracción de datos estáticos

Mover los diccionarios literales a módulos separados en `business/data/`:

**`business/data/nlu_patterns.py`**:
```python
"""Patrones de extracción para NLU basado en keywords."""

INTENT_PATTERNS: dict[str, list[str]] = {
    "route_planning": ["ruta", "llegar", "cómo", "como", "ir", "transporte"],
    "event_search": ["concierto", "evento", "actividad", "plan", "ocio"],
    "restaurant_search": ["restaurante", "comer", "comida"],
    "accommodation_search": ["hotel", "alojamiento", "dormir"],
}

DESTINATION_PATTERNS: dict[str, list[str]] = {
    "Museo del Prado": ["prado", "museo del prado"],
    "Museo Reina Sofía": ["reina sofía", "reina sofia"],
    "Museo Thyssen": ["thyssen"],
    "Parque del Retiro": ["retiro"],
    "Palacio Real": ["palacio real"],
    "Templo de Debod": ["templo debod"],
    # ... rest of patterns
}

ACCESSIBILITY_PATTERNS: dict[str, list[str]] = {
    "wheelchair": ["silla de ruedas", "wheelchair", "accesible", "movilidad"],
    "visual_impairment": ["visual", "ciego", "braille"],
    "hearing_impairment": ["auditivo", "sordo", "señas"],
}
```

**`business/data/accessibility_data.py`**: Extraer el dict `accessibility_db` del `AccessibilityAnalysisTool._run()`.

**`business/data/route_data.py`**: Extraer el dict `route_db` del `RoutePlanningTool._run()`.

**`business/data/venue_data.py`**: Extraer el dict `venue_db` del `TourismInfoTool._run()`.

### 1.6 Refactor de cada tool

Cada tool debe seguir esta estructura:

```python
# business/ai_agents/tools/nlu_tool.py

import json
from datetime import datetime
from langchain.tools import BaseTool
import structlog

from business.data.nlu_patterns import (
    INTENT_PATTERNS,
    DESTINATION_PATTERNS,
    ACCESSIBILITY_PATTERNS,
)
from business.domain.models import NLUResult, TourismIntent, AccessibilityType

logger = structlog.get_logger(__name__)


class TourismNLUTool(BaseTool):
    """Extract intents and entities from Spanish tourism requests."""

    name: str = "tourism_nlu"
    description: str = "Analyze user intent and extract tourism entities from Spanish text"

    def _run(self, user_input: str) -> str:
        user_lower = user_input.lower()

        intent = self._extract_intent(user_lower)
        destination = self._extract_destination(user_lower)
        accessibility = self._extract_accessibility(user_lower)

        result = NLUResult(
            intent=intent,
            destination=destination,
            accessibility_type=accessibility,
            confidence=0.85,
            raw_input=user_input,
        )

        return json.dumps({
            "intent": result.intent.value,
            "entities": {
                "destination": result.destination,
                "accessibility": result.accessibility_type.value,
                "language": "spanish",
            },
            "confidence": result.confidence,
            "timestamp": datetime.now().isoformat(),
        }, indent=2, ensure_ascii=False)

    async def _arun(self, user_input: str) -> str:
        return self._run(user_input)

    def _extract_intent(self, text: str) -> TourismIntent:
        for intent_name, keywords in INTENT_PATTERNS.items():
            if any(kw in text for kw in keywords):
                return TourismIntent(intent_name)
        return TourismIntent.INFORMATION_REQUEST

    def _extract_destination(self, text: str) -> str:
        for dest_name, keywords in DESTINATION_PATTERNS.items():
            if any(kw in text for kw in keywords):
                return dest_name
        return "general"

    def _extract_accessibility(self, text: str) -> AccessibilityType:
        for acc_name, keywords in ACCESSIBILITY_PATTERNS.items():
            if any(kw in text for kw in keywords):
                return AccessibilityType(acc_name)
        return AccessibilityType.GENERAL
```

Aplicar el mismo patrón a `AccessibilityAnalysisTool`, `RoutePlanningTool` y `TourismInfoTool`: separar datos, usar modelos de dominio, mantener la firma de `BaseTool`.

### 1.7 Refactor del orquestador

```python
# business/ai_agents/orchestrator.py

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
import structlog
import os

from shared.interfaces.interfaces import TourismAgentInterface
from business.ai_agents.tools.nlu_tool import TourismNLUTool
from business.ai_agents.tools.accessibility_tool import AccessibilityAnalysisTool
from business.ai_agents.tools.route_planning_tool import RoutePlanningTool
from business.ai_agents.tools.tourism_info_tool import TourismInfoTool
from business.prompts.system_prompt import SYSTEM_PROMPT
from business.prompts.response_prompt import build_response_prompt

logger = structlog.get_logger(__name__)


class TourismMultiAgent(TourismAgentInterface):
    """Orquestador LangChain para turismo accesible."""

    def __init__(self, openai_api_key: Optional[str] = None):
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found.")

        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            openai_api_key=api_key,
            max_tokens=1500,
        )
        self.conversation_history: List[Dict[str, str]] = []
        self.tools = {
            "nlu": TourismNLUTool(),
            "accessibility": AccessibilityAnalysisTool(),
            "route": RoutePlanningTool(),
            "tourism": TourismInfoTool(),
        }

    async def process_request(self, user_input: str) -> Dict[str, Any]:
        nlu_result = self.tools["nlu"]._run(user_input)
        accessibility_result = self.tools["accessibility"]._run(nlu_result)
        route_result = self.tools["route"]._run(accessibility_result)
        tourism_result = self.tools["tourism"]._run(nlu_result)

        prompt = build_response_prompt(
            user_input=user_input,
            nlu_result=nlu_result,
            accessibility_result=accessibility_result,
            route_result=route_result,
            tourism_result=tourism_result,
        )

        response = self.llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)

        self.conversation_history.append({"user": user_input, "assistant": text})

        return {
            "response_text": text,
            "nlu_result": nlu_result,
            "accessibility_info": accessibility_result,
            "route_info": route_result,
            "venue_info": tourism_result,
        }

    # ... get_conversation_history, clear_conversation sin cambios
```

### 1.8 Actualización de `LocalBackendAdapter`

Una vez que `TourismMultiAgent` implementa `TourismAgentInterface`, el adapter ya no necesita reflection con `hasattr()`:

```python
# Cambiar _process_real_query de:
if hasattr(backend, 'process_request_sync'):
    response = await asyncio.to_thread(backend.process_request_sync, ...)
elif hasattr(backend, 'process_request'):
    ...  # 5 fallbacks

# A:
result = await backend.process_request(transcription)
response = result["response_text"]
```

### 1.9 Eliminación de funciones de test

Mover `test_individual_tools()` y `test_orchestrator()` a `tests/test_business/test_tools.py` y `tests/test_business/test_orchestrator.py`. Eliminar el bloque `if __name__` de código de producción.

### 1.10 Checklist de verificación

| # | Tarea | Verificación |
|---|-------|-------------|
| 1 | Crear `business/domain/models.py` | `python -c "from business.domain.models import NLUResult"` |
| 2 | Crear `business/data/nlu_patterns.py` | `python -c "from business.data.nlu_patterns import INTENT_PATTERNS"` |
| 3 | Crear `business/data/accessibility_data.py` | `python -c "from business.data.accessibility_data import ACCESSIBILITY_DB"` |
| 4 | Crear `business/data/route_data.py` | `python -c "from business.data.route_data import ROUTE_DB"` |
| 5 | Crear `business/data/venue_data.py` | `python -c "from business.data.venue_data import VENUE_DB"` |
| 6 | Crear `business/prompts/system_prompt.py` | `python -c "from business.prompts.system_prompt import SYSTEM_PROMPT"` |
| 7 | Crear `business/prompts/response_prompt.py` | `python -c "from business.prompts.response_prompt import build_response_prompt"` |
| 8 | Crear `business/ai_agents/tools/nlu_tool.py` | `python -c "from business.ai_agents.tools.nlu_tool import TourismNLUTool"` |
| 9 | Crear `business/ai_agents/tools/accessibility_tool.py` | Import check |
| 10 | Crear `business/ai_agents/tools/route_planning_tool.py` | Import check |
| 11 | Crear `business/ai_agents/tools/tourism_info_tool.py` | Import check |
| 12 | Crear `business/ai_agents/orchestrator.py` | Import check |
| 13 | Añadir `TourismAgentInterface` a `shared/interfaces/interfaces.py` | Import check |
| 14 | Actualizar `business/ai_agents/__init__.py` | `from business.ai_agents import TourismMultiAgent` |
| 15 | Actualizar `application/orchestration/backend_adapter.py` | Eliminar `hasattr` chain |
| 16 | Eliminar `langchain_agents.py` original | Verificar que no hay imports rotos |
| 17 | Actualizar `langchain_agents.py` (raíz) | Re-export wrapper o eliminar |
| 18 | Mover tests a `tests/test_business/` | `pytest tests/test_business/ -v` |
| 19 | Verificar app completa | `python run-ui.py` arranca sin errores |

### 1.11 Riesgos y consideraciones

- **LangChain API**: Las versiones actuales (`langchain==0.1.0`) usan `BaseTool` con fields Pydantic. Verificar que la firma se mantiene compatible al separar las clases en archivos distintos.
- **Imports circulares**: `business/` no debe importar de `application/` ni `presentation/`. Solo de `shared/` y librerías externas.
- **`asyncio.run()` en `process_request_sync()`**: Esta función falla si ya hay un event loop running (como en FastAPI). El adapter actual lo resuelve con `asyncio.to_thread()`, pero la solución correcta es hacer `process_request` async y llamarlo directamente con `await`.
- **Backwards compatibility**: Mantener el wrapper `langchain_agents.py` en raíz durante esta fase para no romper imports externos.

---

## Fase 2: Dockerización

### 2.1 Contexto

La arquitectura actual corre directamente con `python run-ui.py` y requiere instalación manual de dependencias (Azure SDK, LangChain, Whisper, pydub, etc.). El objetivo es containerizar la aplicación para:

- Reproducibilidad del entorno
- Facilitar despliegues (Azure Container Instances, Azure App Service, o cualquier cloud con soporte Docker)
- Aislar dependencias pesadas (Azure SDK, Whisper models)
- Preparar para escalado horizontal

### 2.2 Arquitectura Docker objetivo

```
voiceFlowPOC/
├── docker-compose.yml              # Orquestación de servicios
├── docker-compose.override.yml     # Overrides para desarrollo local
├── Dockerfile                      # Multi-stage build
├── .dockerignore                   # Excluir archivos innecesarios
├── docker/
│   ├── nginx/
│   │   └── nginx.conf              # Reverse proxy (producción)
│   └── scripts/
│       ├── entrypoint.sh           # Script de entrada del contenedor
│       └── healthcheck.sh          # Script de health check
```

### 2.3 Dockerfile (multi-stage build)

```dockerfile
# ============================================
# Stage 1: Base con dependencias del sistema
# ============================================
FROM python:3.11-slim AS base

# Dependencias del sistema para pydub (ffmpeg) y Azure SDK
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Crear usuario no-root
RUN groupadd -r voiceflow && useradd -r -g voiceflow -d /app -s /sbin/nologin voiceflow

# ============================================
# Stage 2: Instalación de dependencias Python
# ============================================
FROM base AS dependencies

# Copiar solo archivos de dependencias para cache de Docker layers
COPY requirements.txt requirements-ui.txt ./

# Instalar dependencias en un virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -r requirements-ui.txt

# ============================================
# Stage 3: Aplicación final
# ============================================
FROM base AS production

# Copiar virtualenv del stage anterior
COPY --from=dependencies /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código de la aplicación
COPY shared/ /app/shared/
COPY integration/ /app/integration/
COPY business/ /app/business/
COPY application/ /app/application/
COPY presentation/ /app/presentation/
COPY run-ui.py /app/
COPY .env.example /app/.env.example

# Copiar script de entrada
COPY docker/scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Cambiar ownership al usuario no-root
RUN chown -R voiceflow:voiceflow /app

USER voiceflow

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    VOICEFLOW_HOST=0.0.0.0 \
    VOICEFLOW_PORT=8000 \
    VOICEFLOW_DEBUG=false \
    VOICEFLOW_USE_REAL_AGENTS=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "presentation.fastapi_factory:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.4 Script de entrada

```bash
#!/bin/bash
# docker/scripts/entrypoint.sh
set -e

echo "=== VoiceFlow Tourism PoC ==="
echo "Environment: ${VOICEFLOW_DEBUG:-false}"
echo "Real agents: ${VOICEFLOW_USE_REAL_AGENTS:-false}"
echo "Port: ${VOICEFLOW_PORT:-8000}"

# Copiar .env.example si no existe .env
if [ ! -f /app/.env ] && [ -f /app/.env.example ]; then
    echo "No .env found, using .env.example as template"
    cp /app/.env.example /app/.env
fi

# Verificar que las dependencias críticas están disponibles
python -c "import fastapi; import uvicorn; print('Dependencies OK')"

# Ejecutar comando (por defecto: uvicorn)
exec "$@"
```

### 2.5 docker-compose.yml

```yaml
version: "3.9"

services:
  voiceflow-app:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: voiceflow-app
    ports:
      - "${VOICEFLOW_PORT:-8000}:8000"
    environment:
      - VOICEFLOW_HOST=0.0.0.0
      - VOICEFLOW_PORT=8000
      - VOICEFLOW_DEBUG=${VOICEFLOW_DEBUG:-false}
      - VOICEFLOW_USE_REAL_AGENTS=${VOICEFLOW_USE_REAL_AGENTS:-false}
      - VOICEFLOW_LOG_LEVEL=${VOICEFLOW_LOG_LEVEL:-INFO}
      # Secrets via env vars (no hardcodear en compose)
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY:-}
      - AZURE_SPEECH_REGION=${AZURE_SPEECH_REGION:-}
    volumes:
      # Montar .env para configuración local
      - ./.env:/app/.env:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - voiceflow-net

networks:
  voiceflow-net:
    driver: bridge
```

### 2.6 docker-compose.override.yml (desarrollo)

```yaml
version: "3.9"

services:
  voiceflow-app:
    build:
      target: production
    environment:
      - VOICEFLOW_DEBUG=true
      - VOICEFLOW_USE_REAL_AGENTS=false
    volumes:
      # Hot-reload: montar código fuente
      - ./shared:/app/shared:ro
      - ./integration:/app/integration:ro
      - ./business:/app/business:ro
      - ./application:/app/application:ro
      - ./presentation:/app/presentation:ro
      - ./run-ui.py:/app/run-ui.py:ro
    command: >
      uvicorn presentation.fastapi_factory:app
      --host 0.0.0.0
      --port 8000
      --reload
      --reload-dir /app/shared
      --reload-dir /app/integration
      --reload-dir /app/business
      --reload-dir /app/application
      --reload-dir /app/presentation
```

### 2.7 .dockerignore

```
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.egg-info
.eggs
dist
build
*.egg

# Virtual environments
venv
.venv
env

# IDE
.vscode
.idea
*.swp
*.swo

# Documentation (no necesaria en runtime)
documentation/
*.md
!.env.example

# Tests (no necesarios en imagen de producción)
tests/

# Docker (evitar recursión)
docker-compose*.yml
Dockerfile
.dockerignore

# Archivos legacy
web_ui/
src/

# Secrets (nunca incluir en imagen)
.env
*.key
*.pem
```

### 2.8 Cambios necesarios en el código

#### 2.8.1 Prefijo de variables de entorno

`Settings` ya usa `env_prefix="VOICEFLOW_"`, lo cual es correcto para Docker. Las variables de entorno se mapean automáticamente:

| Variable de entorno | Campo en Settings |
|---------------------|-------------------|
| `VOICEFLOW_HOST` | `host` |
| `VOICEFLOW_PORT` | `port` |
| `VOICEFLOW_DEBUG` | `debug` |
| `VOICEFLOW_USE_REAL_AGENTS` | `use_real_agents` |
| `VOICEFLOW_LOG_LEVEL` | `log_level` |

**Excepción**: `OPENAI_API_KEY` y `AZURE_SPEECH_KEY` se leen directamente con `os.getenv()` en `langchain_agents.py` y en `azure_stt_client.py`, sin el prefijo `VOICEFLOW_`. Esto es correcto: son secretos de servicios externos y no deben tener prefijo de la aplicación.

#### 2.8.2 Ajuste de `Settings` para Docker

Añadir campo `environment` a `Settings`:

```python
# En integration/configuration/settings.py
environment: str = Field(default="development", description="Runtime environment: development, staging, production")
```

#### 2.8.3 `host` default

Cambiar el default de `host` en `Settings` de `"localhost"` a leer de entorno. En Docker, el host debe ser `0.0.0.0`. Esto ya se resuelve con la variable `VOICEFLOW_HOST=0.0.0.0` en el compose, pero es bueno que el default sea seguro para local (`localhost`).

#### 2.8.4 Logging a stdout

El logging actual con `structlog` ya emite a stdout (correcto para Docker). No necesita cambios. Los JSON logs son parseables por servicios de logging de contenedores (CloudWatch, Azure Monitor, etc.).

### 2.9 Comandos de operación

```bash
# Construir imagen
docker compose build

# Ejecutar en modo desarrollo (con hot-reload)
docker compose up

# Ejecutar en modo producción
docker compose -f docker-compose.yml up -d

# Ver logs
docker compose logs -f voiceflow-app

# Verificar health
docker compose exec voiceflow-app python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health/').read().decode())"

# Parar y limpiar
docker compose down

# Rebuild sin cache
docker compose build --no-cache
```

### 2.10 Checklist de verificación

| # | Tarea | Verificación |
|---|-------|-------------|
| 1 | Crear `Dockerfile` | `docker build -t voiceflow .` completa sin errores |
| 2 | Crear `.dockerignore` | `docker build` no incluye `.git`, `venv`, `tests/` |
| 3 | Crear `docker/scripts/entrypoint.sh` | Ejecutable, arranca la app |
| 4 | Crear `docker-compose.yml` | `docker compose up` arranca el servicio |
| 5 | Crear `docker-compose.override.yml` | Hot-reload funciona en desarrollo |
| 6 | Verificar health check | `curl http://localhost:8000/api/v1/health/` retorna 200 |
| 7 | Verificar modo simulación | Con `USE_REAL_AGENTS=false`, chat responde sin API keys |
| 8 | Verificar variables de entorno | `OPENAI_API_KEY` se propaga al contenedor |
| 9 | Verificar usuario no-root | `docker exec voiceflow-app whoami` → `voiceflow` |
| 10 | Verificar imagen limpia | `docker images voiceflow` < 500MB |

---

## Fase 3: Testing y validación del software

### 3.1 Objetivo

Implementar una suite de tests completa que cubra los tres niveles del ciclo de verificación: tests unitarios (componentes aislados), tests de integración (colaboración entre capas) y tests end-to-end (sistema completo via HTTP). El proyecto ya tiene la estructura `tests/` creada pero sin tests implementados.

### 3.2 Dependencias de testing

Añadir a `requirements-dev.txt` (nuevo archivo, solo para desarrollo):

```
pytest==7.4.3
pytest-asyncio==0.23.0
pytest-mock==3.12.0
pytest-cov==4.1.0
pytest-xdist==3.5.0          # Ejecución paralela de tests
httpx==0.25.2                 # Cliente async para TestClient
faker==22.0.0                 # Generación de datos de test
```

### 3.3 Configuración pytest

Crear `pyproject.toml` en la raíz del proyecto:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["."]
markers = [
    "unit: Tests unitarios (sin I/O, sin red, sin estado externo)",
    "integration: Tests de integración entre capas (pueden usar filesystem)",
    "e2e: Tests end-to-end contra la API HTTP completa",
    "slow: Tests que tardan más de 5s (requieren API keys o LLM)",
]
filterwarnings = [
    "ignore::DeprecationWarning:langchain.*",
]
addopts = "-ra --strict-markers"

[tool.coverage.run]
source = ["shared", "integration", "business", "application", "presentation"]
omit = ["tests/*", "*/__init__.py"]

[tool.coverage.report]
fail_under = 70
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if __name__",
    "raise NotImplementedError",
]
```

### 3.4 Estructura de tests

```
tests/
├── conftest.py                              # Fixtures globales compartidas
│
├── unit/                                    # ── TESTS UNITARIOS ──
│   ├── conftest.py                          # Fixtures específicas de unit tests
│   ├── test_shared/
│   │   ├── test_interfaces.py               # ABCs: verificar contratos
│   │   └── test_exceptions.py               # Jerarquía + mapeo HTTP
│   ├── test_business/
│   │   ├── test_domain_models.py            # Dataclasses y enums
│   │   ├── test_data_modules.py             # Datos estáticos (patterns, DBs)
│   │   ├── test_nlu_tool.py                 # NLU con inputs variados
│   │   ├── test_accessibility_tool.py       # Análisis de accesibilidad
│   │   ├── test_route_planning_tool.py      # Generación de rutas
│   │   └── test_tourism_info_tool.py        # Info de venues
│   ├── test_application/
│   │   ├── test_request_models.py           # Validación Pydantic requests
│   │   ├── test_response_models.py          # Validación Pydantic responses
│   │   ├── test_audio_service.py            # AudioService con STT mockeado
│   │   └── test_backend_adapter.py          # Adapter con TourismMultiAgent mockeado
│   ├── test_integration/
│   │   ├── test_settings.py                 # Parsing de Settings y env vars
│   │   ├── test_conversation_repository.py  # CRUD in-memory
│   │   └── test_stt_factory.py              # Factory sin servicios reales
│   └── test_presentation/
│       └── test_factory.py                  # create_application() retorna FastAPI
│
├── integration/                             # ── TESTS DE INTEGRACIÓN ──
│   ├── conftest.py                          # Fixtures: app con DI parcial
│   ├── test_stt_pipeline.py                 # Factory → Service → Agent (mocked external)
│   ├── test_chat_pipeline.py                # Endpoint → Adapter → Tools (mocked LLM)
│   ├── test_audio_pipeline.py               # Endpoint → AudioService → Agent (mocked Azure)
│   ├── test_di_wiring.py                    # DI container devuelve tipos correctos
│   └── test_exception_handling.py           # Excepciones → HTTP status codes correctos
│
└── e2e/                                     # ── TESTS END-TO-END ──
    ├── conftest.py                          # Fixtures: TestClient completo
    ├── test_health_flow.py                  # Health checks de todo el sistema
    ├── test_chat_flow.py                    # Flujo completo de chat (simulado)
    ├── test_audio_flow.py                   # Flujo completo de audio (simulado)
    ├── test_conversation_lifecycle.py       # Crear → enviar mensajes → listar → borrar
    ├── test_error_scenarios.py              # Inputs inválidos, archivos corruptos, etc.
    └── test_frontend_rendering.py           # GET / retorna HTML con elementos esperados
```

### 3.5 Fixtures globales

```python
# tests/conftest.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from integration.configuration.settings import Settings


@pytest.fixture
def mock_settings():
    """Settings sin credenciales reales, modo simulación."""
    return Settings(
        debug=True,
        use_real_agents=False,
        azure_speech_key=None,
        azure_speech_region=None,
        openai_api_key=None,
        host="127.0.0.1",
        port=8000,
    )


@pytest.fixture
def mock_stt_result():
    """Resultado simulado de transcripción STT."""
    return type("Result", (), {
        "transcription": "Necesito una ruta accesible al Museo del Prado",
        "confidence": 0.92,
        "language": "es-ES",
        "duration": 3.5,
        "processing_time": 1.0,
    })()


@pytest.fixture
def mock_audio_data():
    """Bytes mínimos que simulan un archivo WAV válido."""
    # RIFF header + minimal WAV structure
    return (
        b"RIFF" + (36).to_bytes(4, "little") +
        b"WAVEfmt " + (16).to_bytes(4, "little") +
        (1).to_bytes(2, "little") +    # PCM
        (1).to_bytes(2, "little") +    # mono
        (16000).to_bytes(4, "little") + # sample rate
        (32000).to_bytes(4, "little") + # byte rate
        (2).to_bytes(2, "little") +    # block align
        (16).to_bytes(2, "little") +   # bits per sample
        b"data" + (0).to_bytes(4, "little")
    )


@pytest.fixture
def sample_chat_messages():
    """Mensajes de prueba en español para el NLU."""
    return [
        ("Cómo llego al Museo del Prado en silla de ruedas", "route_planning", "Museo del Prado", "wheelchair"),
        ("Restaurantes accesibles cerca del centro", "restaurant_search", "Restaurantes Madrid", "general"),
        ("Conciertos para personas con discapacidad auditiva", "event_search", "Espacios musicales Madrid", "hearing_impairment"),
        ("Información sobre el Museo Reina Sofía", "information_request", "Museo Reina Sofía", "general"),
        ("Hoteles accesibles en Madrid", "accommodation_search", "general", "general"),
        ("Hola, qué tal", "information_request", "general", "general"),
    ]
```

### 3.6 Tests unitarios — Detalle por capa

#### 3.6.1 Shared layer

```python
# tests/unit/test_shared/test_interfaces.py

import pytest
from shared.interfaces.interfaces import (
    AudioProcessorInterface, BackendInterface, ConversationInterface
)
from application.services.audio_service import AudioService
from application.orchestration.backend_adapter import LocalBackendAdapter
from integration.data_persistence.conversation_repository import ConversationService


@pytest.mark.unit
class TestInterfaceCompliance:
    """Verificar que las implementaciones cumplen los contratos ABC."""

    def test_audio_service_implements_interface(self):
        assert issubclass(AudioService, AudioProcessorInterface)

    def test_backend_adapter_implements_interface(self):
        assert issubclass(LocalBackendAdapter, BackendInterface)

    def test_conversation_service_implements_interface(self):
        assert issubclass(ConversationService, ConversationInterface)


# tests/unit/test_shared/test_exceptions.py

@pytest.mark.unit
class TestExceptionMapping:
    """Verificar mapeo excepción → HTTP status code."""

    def test_audio_processing_maps_to_422(self):
        from shared.exceptions.exceptions import (
            AudioProcessingException, EXCEPTION_STATUS_CODES
        )
        assert EXCEPTION_STATUS_CODES[AudioProcessingException] == 422

    def test_validation_maps_to_400(self):
        from shared.exceptions.exceptions import (
            ValidationException, EXCEPTION_STATUS_CODES
        )
        assert EXCEPTION_STATUS_CODES[ValidationException] == 400

    def test_backend_communication_maps_to_503(self):
        from shared.exceptions.exceptions import (
            BackendCommunicationException, EXCEPTION_STATUS_CODES
        )
        assert EXCEPTION_STATUS_CODES[BackendCommunicationException] == 503

    def test_all_exceptions_have_message_and_error_code(self):
        from shared.exceptions.exceptions import VoiceFlowException
        exc = VoiceFlowException("test msg", error_code="TEST_001")
        assert exc.message == "test msg"
        assert exc.error_code == "TEST_001"
```

#### 3.6.2 Business layer (tools)

Estos tests son los más críticos y los más fáciles de escribir: los tools son funciones puras con datos estáticos, sin dependencias externas.

```python
# tests/unit/test_business/test_nlu_tool.py

import json
import pytest
from business.ai_agents.langchain_agents import TourismNLUTool


@pytest.mark.unit
class TestTourismNLUTool:

    @pytest.fixture
    def tool(self):
        return TourismNLUTool()

    @pytest.mark.parametrize("input_text,expected_intent", [
        ("Cómo llego al Museo del Prado", "route_planning"),
        ("Restaurantes accesibles", "restaurant_search"),
        ("Conciertos en Madrid", "event_search"),
        ("Hoteles para personas con movilidad reducida", "accommodation_search"),
        ("Hola buenas tardes", "information_request"),  # fallback
    ])
    def test_intent_detection(self, tool, input_text, expected_intent):
        result = json.loads(tool._run(input_text))
        assert result["intent"] == expected_intent

    @pytest.mark.parametrize("input_text,expected_destination", [
        ("Quiero ir al Museo del Prado", "Museo del Prado"),
        ("Información del Museo Reina Sofía", "Museo Reina Sofía"),
        ("Visitar el Thyssen", "Museo Thyssen"),
        ("Paseo por el Retiro", "Parque del Retiro"),
        ("Qué tiempo hace hoy", "general"),  # sin destino
    ])
    def test_destination_extraction(self, tool, input_text, expected_destination):
        result = json.loads(tool._run(input_text))
        assert result["entities"]["destination"] == expected_destination

    @pytest.mark.parametrize("input_text,expected_accessibility", [
        ("Acceso en silla de ruedas", "wheelchair"),
        ("Información para personas ciegas", "visual_impairment"),
        ("Intérprete de lengua de señas", "hearing_impairment"),
        ("Información general", "general"),  # fallback
    ])
    def test_accessibility_extraction(self, tool, input_text, expected_accessibility):
        result = json.loads(tool._run(input_text))
        assert result["entities"]["accessibility"] == expected_accessibility

    def test_output_has_required_fields(self, tool):
        result = json.loads(tool._run("cualquier texto"))
        assert "intent" in result
        assert "entities" in result
        assert "confidence" in result
        assert "timestamp" in result
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1

    def test_empty_input_returns_defaults(self, tool):
        result = json.loads(tool._run(""))
        assert result["intent"] == "information_request"
        assert result["entities"]["destination"] == "general"


# tests/unit/test_business/test_accessibility_tool.py

@pytest.mark.unit
class TestAccessibilityAnalysisTool:

    @pytest.fixture
    def tool(self):
        from business.ai_agents.langchain_agents import AccessibilityAnalysisTool
        return AccessibilityAnalysisTool()

    def test_known_venue_returns_specific_data(self, tool):
        nlu_input = json.dumps({
            "entities": {"destination": "Museo del Prado", "accessibility": "wheelchair"}
        })
        result = json.loads(tool._run(nlu_input))
        assert result["accessibility_score"] >= 9.0
        assert "wheelchair_ramps" in result["facilities"]
        assert result["certification"] == "ONCE_certified"

    def test_unknown_venue_returns_defaults(self, tool):
        nlu_input = json.dumps({
            "entities": {"destination": "Lugar inexistente", "accessibility": "general"}
        })
        result = json.loads(tool._run(nlu_input))
        assert result["accessibility_score"] == 6.0

    def test_malformed_json_input_uses_defaults(self, tool):
        result = json.loads(tool._run("esto no es JSON"))
        assert "accessibility_level" in result
        assert "accessibility_score" in result


# tests/unit/test_business/test_route_planning_tool.py

@pytest.mark.unit
class TestRoutePlanningTool:

    @pytest.fixture
    def tool(self):
        from business.ai_agents.langchain_agents import RoutePlanningTool
        return RoutePlanningTool()

    def test_prado_routes_include_metro_and_bus(self, tool):
        result = json.loads(tool._run("Museo del Prado wheelchair access"))
        routes = result["routes"]
        transports = [r["transport"] for r in routes]
        assert "metro" in transports
        assert "bus" in transports

    def test_routes_have_required_fields(self, tool):
        result = json.loads(tool._run("Prado"))
        for route in result["routes"]:
            assert "transport" in route
            assert "duration" in route
            assert "accessibility" in route
            assert "steps" in route
            assert isinstance(route["steps"], list)


# tests/unit/test_business/test_tourism_info_tool.py

@pytest.mark.unit
class TestTourismInfoTool:

    @pytest.fixture
    def tool(self):
        from business.ai_agents.langchain_agents import TourismInfoTool
        return TourismInfoTool()

    def test_prado_has_pricing_and_hours(self, tool):
        result = json.loads(tool._run("Museo del Prado"))
        assert "opening_hours" in result
        assert "pricing" in result
        assert "general" in result["pricing"]

    def test_unknown_venue_returns_generic_info(self, tool):
        result = json.loads(tool._run("lugar desconocido"))
        assert result["venue"] == "General Madrid"
        assert "opening_hours" in result
```

#### 3.6.3 Application layer

```python
# tests/unit/test_application/test_request_models.py

import pytest
from pydantic import ValidationError
from application.models.requests import ChatMessageRequest


@pytest.mark.unit
class TestChatMessageRequest:

    def test_valid_message(self):
        req = ChatMessageRequest(message="Hola mundo")
        assert req.message == "Hola mundo"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatMessageRequest(message="")

    def test_message_max_length(self):
        with pytest.raises(ValidationError):
            ChatMessageRequest(message="x" * 1001)

    def test_optional_fields_default_none(self):
        req = ChatMessageRequest(message="test")
        assert req.conversation_id is None or isinstance(req.conversation_id, str)


# tests/unit/test_application/test_backend_adapter.py

@pytest.mark.unit
class TestLocalBackendAdapter:

    @pytest.fixture
    def adapter(self, mock_settings):
        mock_settings.use_real_agents = False
        from application.orchestration.backend_adapter import LocalBackendAdapter
        return LocalBackendAdapter(mock_settings)

    @pytest.mark.asyncio
    async def test_simulation_mode_returns_response(self, adapter):
        result = await adapter.process_query("Museo del Prado")
        assert result["success"] is True
        assert "ai_response" in result
        assert len(result["ai_response"]) > 0
        assert result["processing_details"]["backend_type"] == "simulated_demo"

    @pytest.mark.asyncio
    async def test_simulation_prado_mentions_prado(self, adapter):
        result = await adapter.process_query("Museo del Prado")
        assert "Prado" in result["ai_response"]

    @pytest.mark.asyncio
    async def test_simulation_generic_query(self, adapter):
        result = await adapter.process_query("algo genérico")
        assert result["success"] is True
        assert "ai_response" in result

    @pytest.mark.asyncio
    async def test_conversation_counter_increments(self, adapter):
        await adapter.process_query("test 1")
        await adapter.process_query("test 2")
        assert adapter._conversation_count == 2

    @pytest.mark.asyncio
    async def test_get_system_status_without_backend(self, adapter):
        # Sin OPENAI_API_KEY, get_system_status debería manejar el error
        status = await adapter.get_system_status()
        assert "status" in status


# tests/unit/test_application/test_audio_service.py

@pytest.mark.unit
class TestAudioService:

    @pytest.fixture
    def service(self, mock_settings):
        from application.services.audio_service import AudioService
        return AudioService(mock_settings)

    @pytest.mark.asyncio
    async def test_get_supported_formats(self, service):
        formats = await service.get_supported_formats()
        assert isinstance(formats, list)
        assert "wav" in formats

    @pytest.mark.asyncio
    async def test_transcribe_audio_fallback(self, service, mock_audio_data):
        """Sin Azure SDK, debe retornar resultado simulado."""
        result = await service.transcribe_audio(mock_audio_data, "audio/wav", "es-ES")
        assert hasattr(result, "transcription")
        assert hasattr(result, "confidence")
```

#### 3.6.4 Integration layer

```python
# tests/unit/test_integration/test_settings.py

import os
import pytest


@pytest.mark.unit
class TestSettings:

    def test_default_values(self):
        from integration.configuration.settings import Settings
        s = Settings()
        assert s.app_name == "VoiceFlow Tourism PoC"
        assert s.port == 8000
        assert s.debug is True

    def test_env_prefix_voiceflow(self, monkeypatch):
        monkeypatch.setenv("VOICEFLOW_PORT", "9999")
        monkeypatch.setenv("VOICEFLOW_DEBUG", "false")
        from integration.configuration.settings import Settings
        s = Settings()
        assert s.port == 9999
        assert s.debug is False

    def test_use_real_agents_default_true(self):
        from integration.configuration.settings import Settings
        s = Settings()
        assert s.use_real_agents is True


# tests/unit/test_integration/test_conversation_repository.py

@pytest.mark.unit
class TestConversationRepository:

    @pytest.fixture
    def repo(self, mock_settings):
        from integration.data_persistence.conversation_repository import ConversationService
        return ConversationService(mock_settings)

    @pytest.mark.asyncio
    async def test_create_conversation(self, repo):
        conv_id = await repo.create_conversation()
        assert isinstance(conv_id, str)
        assert len(conv_id) > 0

    @pytest.mark.asyncio
    async def test_add_message_and_retrieve(self, repo):
        conv_id = await repo.create_conversation()
        await repo.add_message("Hola", "Buenos días", conv_id)
        history = await repo.get_conversation_history(conv_id)
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_clear_conversation(self, repo):
        conv_id = await repo.create_conversation()
        await repo.add_message("test", "response", conv_id)
        result = await repo.clear_conversation(conv_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, repo):
        history = await repo.get_conversation_history("nonexistent_id")
        assert history == [] or history is None
```

### 3.7 Tests de integración — Detalle

Los tests de integración verifican que múltiples componentes colaboran correctamente. Usan la app FastAPI real pero con servicios externos mockeados.

```python
# tests/integration/conftest.py

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from integration.configuration.settings import Settings


@pytest.fixture
def test_settings():
    """Settings para integración: simulación, sin API keys."""
    return Settings(
        debug=True,
        use_real_agents=False,
        azure_speech_key=None,
        openai_api_key=None,
    )


@pytest.fixture
def test_client(test_settings):
    """TestClient con la app completa pero en modo simulación."""
    # Forzar settings de test
    from integration.configuration.settings import get_settings
    from presentation.fastapi_factory import create_application

    app = create_application()

    # Override DI para usar test settings
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as client:
        yield client


# tests/integration/test_di_wiring.py

@pytest.mark.integration
class TestDIWiring:
    """Verificar que el contenedor DI conecta interfaces con implementaciones."""

    def test_audio_processor_returns_audio_service(self, test_settings):
        from shared.utils.dependencies import get_audio_processor
        from application.services.audio_service import AudioService
        processor = get_audio_processor(test_settings)
        assert isinstance(processor, AudioService)

    def test_backend_adapter_returns_local_adapter(self, test_settings):
        from shared.utils.dependencies import get_backend_adapter
        from application.orchestration.backend_adapter import LocalBackendAdapter
        adapter = get_backend_adapter(test_settings)
        assert isinstance(adapter, LocalBackendAdapter)

    def test_conversation_service_returns_conversation_service(self, test_settings):
        from shared.utils.dependencies import get_conversation_service
        from application.services.conversation_service import ConversationService
        service = get_conversation_service(test_settings)
        assert isinstance(service, ConversationService)


# tests/integration/test_chat_pipeline.py

@pytest.mark.integration
class TestChatPipeline:
    """Verifica el pipeline completo: endpoint → adapter → tools (modo simulación)."""

    def test_chat_message_returns_ai_response(self, test_client):
        response = test_client.post("/api/v1/chat/message", json={
            "message": "Cómo llego al Museo del Prado en silla de ruedas"
        })
        assert response.status_code == 200
        data = response.json()
        assert "ai_response" in data
        assert len(data["ai_response"]) > 50  # respuesta sustancial
        assert "Prado" in data["ai_response"]

    def test_chat_returns_processing_details(self, test_client):
        response = test_client.post("/api/v1/chat/message", json={
            "message": "Restaurantes accesibles"
        })
        data = response.json()
        assert data.get("status") == "success"

    def test_chat_invalid_empty_message(self, test_client):
        response = test_client.post("/api/v1/chat/message", json={
            "message": ""
        })
        assert response.status_code == 422  # Pydantic validation


# tests/integration/test_audio_pipeline.py

@pytest.mark.integration
class TestAudioPipeline:
    """Verifica el pipeline: endpoint → AudioService → transcripción (fallback)."""

    def test_transcribe_with_wav_file(self, test_client, mock_audio_data):
        response = test_client.post(
            "/api/v1/audio/transcribe",
            files={"audio_file": ("test.wav", mock_audio_data, "audio/wav")},
            data={"language": "es-ES"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "transcription" in data
        assert "confidence" in data

    def test_transcribe_empty_file_returns_400(self, test_client):
        response = test_client.post(
            "/api/v1/audio/transcribe",
            files={"audio_file": ("empty.wav", b"", "audio/wav")},
        )
        assert response.status_code == 400

    def test_validate_audio_endpoint(self, test_client, mock_audio_data):
        response = test_client.post(
            "/api/v1/audio/validate",
            files={"audio_file": ("test.wav", mock_audio_data, "audio/wav")},
        )
        assert response.status_code == 200


# tests/integration/test_exception_handling.py

@pytest.mark.integration
class TestExceptionHandling:
    """Verificar que excepciones de dominio se mapean a HTTP status correctos."""

    def test_voiceflow_exception_returns_json(self, test_client):
        """Las excepciones no deben retornar stack traces al cliente."""
        # Provocar un error interno con input problemático
        response = test_client.post("/api/v1/chat/message", json={
            "message": "x" * 1001  # exceeds max_length
        })
        assert response.status_code in [400, 422]
        data = response.json()
        # No debe contener stack traces
        assert "Traceback" not in str(data)

    def test_404_for_unknown_endpoint(self, test_client):
        response = test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
```

### 3.8 Tests end-to-end — Detalle

Los tests E2E verifican flujos completos de usuario contra la API HTTP, como los usaría el frontend. Siempre en modo simulación (sin API keys).

```python
# tests/e2e/conftest.py

import pytest
from fastapi.testclient import TestClient
from integration.configuration.settings import Settings, get_settings
from presentation.fastapi_factory import create_application


@pytest.fixture(scope="module")
def e2e_client():
    """TestClient con scope de módulo para reutilizar entre tests E2E."""
    test_settings = Settings(
        debug=True,
        use_real_agents=False,
    )
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as client:
        yield client


# tests/e2e/test_health_flow.py

@pytest.mark.e2e
class TestHealthFlow:

    def test_main_health_returns_200(self, e2e_client):
        r = e2e_client.get("/api/v1/health/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ["success", "warning", "error"]
        assert "components" in data
        assert "version" in data

    def test_backend_health(self, e2e_client):
        r = e2e_client.get("/api/v1/health/backend")
        assert r.status_code == 200
        assert "status" in r.json()

    def test_audio_health(self, e2e_client):
        r = e2e_client.get("/api/v1/health/audio")
        assert r.status_code == 200
        data = r.json()
        assert "supported_formats" in data


# tests/e2e/test_chat_flow.py

@pytest.mark.e2e
class TestChatFlow:

    def test_simple_question_and_response(self, e2e_client):
        r = e2e_client.post("/api/v1/chat/message", json={
            "message": "Información sobre el Museo del Prado"
        })
        assert r.status_code == 200
        data = r.json()
        assert "ai_response" in data
        assert len(data["ai_response"]) > 20

    def test_demo_responses_endpoint(self, e2e_client):
        r = e2e_client.get("/api/v1/chat/demo/responses")
        assert r.status_code == 200

    def test_multiple_queries_in_sequence(self, e2e_client):
        """Simula una conversación con múltiples preguntas."""
        queries = [
            "Hola, necesito información turística",
            "Cómo llego al Museo del Prado",
            "Restaurantes accesibles cerca",
        ]
        for query in queries:
            r = e2e_client.post("/api/v1/chat/message", json={"message": query})
            assert r.status_code == 200
            assert "ai_response" in r.json()


# tests/e2e/test_conversation_lifecycle.py

@pytest.mark.e2e
class TestConversationLifecycle:

    def test_list_conversations(self, e2e_client):
        r = e2e_client.get("/api/v1/chat/conversations")
        assert r.status_code == 200

    def test_create_and_retrieve_conversation(self, e2e_client):
        # Enviar mensaje (crea conversación implícitamente)
        r1 = e2e_client.post("/api/v1/chat/message", json={
            "message": "Test de ciclo de vida",
            "conversation_id": "lifecycle_test_001",
        })
        assert r1.status_code == 200

        # Obtener historial
        r2 = e2e_client.get("/api/v1/chat/conversation/lifecycle_test_001")
        assert r2.status_code in [200, 404]  # 404 si no persiste entre requests


# tests/e2e/test_error_scenarios.py

@pytest.mark.e2e
class TestErrorScenarios:

    def test_chat_without_message_field(self, e2e_client):
        r = e2e_client.post("/api/v1/chat/message", json={})
        assert r.status_code == 422

    def test_chat_with_wrong_content_type(self, e2e_client):
        r = e2e_client.post(
            "/api/v1/chat/message",
            content="plain text",
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 422

    def test_audio_transcribe_without_file(self, e2e_client):
        r = e2e_client.post("/api/v1/audio/transcribe")
        assert r.status_code == 422

    def test_async_status_nonexistent_id(self, e2e_client):
        r = e2e_client.get("/api/v1/audio/transcribe-status/nonexistent-uuid")
        assert r.status_code == 404


# tests/e2e/test_frontend_rendering.py

@pytest.mark.e2e
class TestFrontendRendering:

    def test_root_returns_html(self, e2e_client):
        r = e2e_client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_html_contains_voiceflow_branding(self, e2e_client):
        r = e2e_client.get("/")
        assert "VoiceFlow" in r.text

    def test_html_loads_js_files(self, e2e_client):
        r = e2e_client.get("/")
        assert "/static/js/app.js" in r.text
        assert "/static/js/audio.js" in r.text
        assert "/static/js/chat.js" in r.text

    def test_static_css_accessible(self, e2e_client):
        r = e2e_client.get("/static/css/app.css")
        assert r.status_code == 200

    def test_static_js_accessible(self, e2e_client):
        for js_file in ["app.js", "audio.js", "chat.js"]:
            r = e2e_client.get(f"/static/js/{js_file}")
            assert r.status_code == 200, f"{js_file} not accessible"
```

### 3.9 Comandos de ejecución

```bash
# ── Ejecutar por nivel ──

# Solo unit tests (rápidos, sin I/O)
pytest tests/unit/ -m unit -v

# Solo integration tests
pytest tests/integration/ -m integration -v

# Solo E2E tests
pytest tests/e2e/ -m e2e -v

# ── Todos los tests ──
pytest tests/ -v --tb=short

# ── Con coverage ──
pytest tests/ --cov --cov-report=html --cov-report=term-missing

# ── Ejecución paralela (acelera suites grandes) ──
pytest tests/ -n auto

# ── Solo tests de una capa específica ──
pytest tests/unit/test_business/ -v
pytest tests/unit/test_application/ -v

# ── Excluir tests lentos (que requieren API keys) ──
pytest tests/ -m "not slow" -v

# ── Dentro de Docker ──
docker compose run --rm voiceflow-app pytest tests/ -v --tb=short
```

### 3.10 Objetivos de cobertura

| Capa | Cobertura mínima | Prioridad | Justificación |
|------|-------------------|-----------|---------------|
| `shared/` | 90% | Alta | Son contratos y excepciones — deben ser exhaustivos |
| `business/` (tools) | 85% | Alta | Funciones puras con datos estáticos, fáciles de testear |
| `business/` (orchestrator) | 60% | Media | Requiere mock de LLM, más complejo |
| `application/api/` | 80% | Alta | Endpoints son la interfaz pública del sistema |
| `application/services/` | 75% | Alta | Lógica de coordinación con fallbacks |
| `application/orchestration/` | 70% | Media | Adapter con modo simulación y modo real |
| `integration/configuration/` | 80% | Media | Parsing de settings es crítico para deploys |
| `integration/external_apis/` | 50% | Baja | Depende de servicios externos, testing limitado sin API keys |
| `integration/data_persistence/` | 85% | Alta | CRUD in-memory, fácil de testear |
| `presentation/` | 60% | Media | Factory y rendering, verificación básica |
| **Global** | **70%** | — | Umbral mínimo en `pyproject.toml` |

### 3.11 Orden de implementación

| # | Paquete de tests | Dependencia | Razón del orden |
|---|-----------------|-------------|-----------------|
| 1 | `tests/conftest.py` + `pyproject.toml` | Ninguna | Infraestructura base |
| 2 | `tests/unit/test_shared/` | #1 | Sin dependencias, valida contratos |
| 3 | `tests/unit/test_business/` (tools) | #1 | Funciones puras, máximo valor por esfuerzo |
| 4 | `tests/unit/test_integration/test_settings.py` | #1 | Configuración crítica para todo lo demás |
| 5 | `tests/unit/test_integration/test_conversation_repository.py` | #1 | CRUD simple, independiente |
| 6 | `tests/unit/test_application/test_*_models.py` | #1 | Validación Pydantic |
| 7 | `tests/unit/test_application/test_backend_adapter.py` | #3 | Requiere entender tools |
| 8 | `tests/unit/test_application/test_audio_service.py` | #1 | Servicio con fallback |
| 9 | `tests/integration/test_di_wiring.py` | #1 | Verificar DI antes de testear endpoints |
| 10 | `tests/integration/test_chat_pipeline.py` | #7, #9 | Pipeline completo de chat |
| 11 | `tests/integration/test_audio_pipeline.py` | #8, #9 | Pipeline completo de audio |
| 12 | `tests/integration/test_exception_handling.py` | #9 | Mapeo excepciones → HTTP |
| 13 | `tests/e2e/test_health_flow.py` | #9 | Smoke test del sistema |
| 14 | `tests/e2e/test_chat_flow.py` | #10 | Flujo E2E de chat |
| 15 | `tests/e2e/test_audio_flow.py` | #11 | Flujo E2E de audio |
| 16 | `tests/e2e/test_conversation_lifecycle.py` | #14 | CRUD completo via HTTP |
| 17 | `tests/e2e/test_error_scenarios.py` | #12 | Inputs inválidos y edge cases |
| 18 | `tests/e2e/test_frontend_rendering.py` | #13 | Verificación HTML y estáticos |
| 19 | `tests/unit/test_presentation/test_factory.py` | #9 | Creación de app |

### 3.12 Checklist de verificación

| # | Tarea | Verificación |
|---|-------|-------------|
| 1 | Crear `pyproject.toml` con config pytest | `pytest --collect-only` lista tests |
| 2 | Crear `tests/conftest.py` con fixtures globales | `pytest tests/unit/test_shared/ -v` pasa |
| 3 | Implementar tests unitarios shared | `pytest tests/unit/test_shared/ -v` ≥ 90% cov |
| 4 | Implementar tests unitarios business tools | `pytest tests/unit/test_business/ -v` ≥ 85% cov |
| 5 | Implementar tests unitarios application | `pytest tests/unit/test_application/ -v` ≥ 75% cov |
| 6 | Implementar tests unitarios integration | `pytest tests/unit/test_integration/ -v` ≥ 80% cov |
| 7 | Implementar tests de integración | `pytest tests/integration/ -v` todos pasan |
| 8 | Implementar tests E2E | `pytest tests/e2e/ -v` todos pasan |
| 9 | Coverage global ≥ 70% | `pytest --cov --cov-fail-under=70` pasa |
| 10 | Tests pasan en Docker | `docker compose run --rm voiceflow-app pytest` pasa |
| 11 | Tests pasan sin API keys | `pytest -m "not slow"` pasa sin `.env` |
| 12 | Ningún test modifica estado global | Tests pasan con `pytest -n auto` (paralelo) |

### 3.13 Integración con CI/CD (Fase 7)

```yaml
# En .github/workflows/ci.yml, el job "test" ejecutará:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt
      - run: pytest tests/unit/ tests/integration/ -v --tb=short --junitxml=results.xml -m "not slow"
      - run: pytest tests/ --cov --cov-report=xml --cov-fail-under=70
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/

  e2e:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build
      - run: docker compose run --rm voiceflow-app pytest tests/e2e/ -v --tb=short
```

---

## Fase 4: Persistencia real

### 4.1 Objetivo

Reemplazar el almacenamiento in-memory de conversaciones (`ConversationService` con `self.conversations: Dict`) por una base de datos real.

### 4.2 Opciones

| Opción | Complejidad | Ideal para |
|--------|-------------|------------|
| SQLite + SQLAlchemy | Baja | PoC, desarrollo local, despliegue single-instance |
| PostgreSQL + SQLAlchemy | Media | Producción, multi-instance, Azure Database for PostgreSQL |
| Azure Cosmos DB | Media-Alta | Full Azure ecosystem, escalabilidad global |

**Recomendación para este PoC**: SQLite para desarrollo, PostgreSQL para producción (ambos via SQLAlchemy con el mismo código, cambiando solo `DATABASE_URL`).

### 4.3 Tareas

1. Añadir `sqlalchemy` y `alembic` a dependencias
2. Crear modelos SQLAlchemy en `integration/data_persistence/models.py`
3. Implementar `SQLConversationRepository(ConversationInterface)` en `integration/data_persistence/`
4. Actualizar DI en `dependencies.py` para inyectar la nueva implementación según `database_enabled`
5. Crear migraciones con Alembic
6. Añadir servicio `db` en `docker-compose.yml` (PostgreSQL) para producción
7. Actualizar `Settings` con `DATABASE_URL` real

### 4.4 Modelo de datos propuesto

```python
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String, index=True)
    topic = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String)  # "user" | "assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column(JSON, nullable=True)
```

---

## Fase 5: Observabilidad y monitoring

### 5.1 Objetivo

Instrumentar la aplicación para tener visibilidad sobre rendimiento, errores y uso en producción.

### 5.2 Tareas

1. **Métricas con Prometheus**: Añadir `prometheus-fastapi-instrumentator` para métricas automáticas de endpoints (latencia, throughput, error rate)
2. **Tracing con OpenTelemetry**: Instrumentar el pipeline STT → NLU → Tools → LLM para ver latencia de cada paso
3. **Dashboard**: Configurar Grafana como servicio en `docker-compose.yml` (solo en development/staging)
4. **Alertas**: Definir alertas para:
   - Latencia de respuesta > 10s
   - Error rate > 5%
   - Memoria del contenedor > 80%
   - Health check fallido
5. **Logging estructurado**: Ya implementado con `structlog`. Añadir correlation IDs (request ID) para trazar requests end-to-end

### 5.3 Servicios Docker adicionales

```yaml
# Añadir a docker-compose.override.yml (solo desarrollo)
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Fase 6: Seguridad y autenticación

### 6.1 Objetivo

Implementar las interfaces `AuthInterface` y securizar la API.

### 6.2 Tareas

1. **Headers de seguridad**: Añadir middleware para `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`
2. **Rate limiting**: Añadir `slowapi` para limitar requests por IP (prevenir abuso de API de audio/chat)
3. **Implementar `AuthInterface`**: JWT con `python-jose` (ya es dependencia) o Azure AD B2C para entorno Azure
4. **Proteger endpoints sensibles**: Chat y audio requieren autenticación; health público
5. **CORS restrictivo**: Configurar orígenes específicos para producción (no `*`)
6. **Secrets management**: Migrar de `.env` a Azure Key Vault o Docker secrets para producción

### 6.3 Middleware de seguridad propuesto

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
```

---

## Fase 7: CI/CD pipeline

### 7.1 Objetivo

Automatizar build, test y deploy del proyecto.

### 7.2 Pipeline propuesto (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-ui.txt
      - run: pytest tests/ -v --tb=short --junitxml=results.xml

  docker-build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t voiceflow:${{ github.sha }} .
      - run: |
          docker run -d --name test-container -p 8000:8000 \
            -e VOICEFLOW_USE_REAL_AGENTS=false \
            voiceflow:${{ github.sha }}
          sleep 10
          curl -f http://localhost:8000/api/v1/health/ || exit 1
          docker stop test-container

  deploy:
    runs-on: ubuntu-latest
    needs: docker-build
    if: github.ref == 'refs/heads/main'
    steps:
      # Deploy a Azure Container Instances / App Service
      - run: echo "Deploy step - configure for target platform"
```

### 7.3 Tareas

1. Crear `.github/workflows/ci.yml` con lint + test + docker build
2. Configurar secrets en GitHub (API keys para tests de integración)
3. Añadir linter (`ruff`) y formateador (`ruff format`)
4. Configurar deploy automático al merge en `main`

---

## Fase 8: Deuda técnica transversal

Tareas que pueden ejecutarse en paralelo con cualquier fase:

| # | Tarea | Impacto | Fase relacionada |
|---|-------|---------|------------------|
| 1 | Eliminar `server_launcher.py` (duplica `run-ui.py`) | Bajo | Cualquiera |
| 2 | Eliminar `SimulatedAudioService` de `dependencies.py` (no implementa interfaz) | Bajo | Fase 3 |
| 3 | Eliminar `initialize_services()` globals duplicadas | Bajo | Fase 3 |
| 4 | Mover `dependencies.py` de `shared/utils/` a `application/` | Medio | Fase 1 |
| 5 | Unificar `requirements.txt` y `requirements-ui.txt` en uno solo | Bajo | Fase 2 |
| 6 | Fijar variables Jinja2 en `index.html` (`title` → `app_name`, `environment`) | Bajo | Cualquiera |
| 7 | Conectar templates `404.html` y `500.html` a handlers | Bajo | Cualquiera |
| 8 | Fix `AudioService.validate_audio` dual (dos métodos con mismo nombre) | Medio | Fase 3 |
| 9 | Eliminar `_simulate_ai_response()` (~110 líneas) del adapter y moverlo a un mock service | Medio | Fase 1 |
| 10 | Consolidar `conversation_service.py` (application) y `conversation_repository.py` (integration) — son copias | Medio | Fase 4 |
| 11 | Añadir CDN fallback local para Bootstrap | Bajo | Fase 6 |
| 12 | Generar `conversation_id` en backend con UUID en vez de en frontend con `Date.now()` | Medio | Fase 4 |

---

## Resumen de prioridades

```
                          IMPACTO EN CALIDAD
                    Bajo         Medio        Alto
                 ┌───────────┬────────────┬───────────┐
            Alta │           │            │  Fase 1   │
                 │           │            │  Fase 2   │
   URGENCIA      ├───────────┼────────────┼───────────┤
            Med  │  Fase 8   │  Fase 4    │  Fase 3   │
                 │           │  Fase 5    │           │
                 ├───────────┼────────────┼───────────┤
            Baja │           │  Fase 6    │  Fase 7   │
                 │           │            │           │
                 └───────────┴────────────┴───────────┘
```

**Orden recomendado**: 1 → 2 → 3 → 4 → 5 → 6 → 7 (con Fase 8 en paralelo).

Las Fases 1 y 2 son las más urgentes porque desbloquean todo lo demás: sin la descomposición del monolito no se pueden escribir tests granulares de la business layer, y sin Docker no se puede automatizar CI/CD ni garantizar reproducibilidad.
