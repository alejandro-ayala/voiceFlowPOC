# Guía de Desarrollo - VoiceflowSTTAgent

## 🚀 Setup de Desarrollo

### Prerrequisitos
- Python 3.9+
- Git
- Editor con soporte para type hints (VS Code recomendado)

### Configuración Inicial del Entorno

1. **Clonar y navegar al proyecto:**
   ```bash
   cd d:\Code\TurismoReducido\VoiceFlowPOC
   ```

2. **Crear entorno virtual:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Instalar dependencias de desarrollo:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

### Estructura de Desarrollo
```
VoiceFlowPOC/
├── main.py                      # 🎯 Aplicación principal
├── langchain_agents.py          # 🤖 Sistema multi-agente LangChain
├── test_voiceflow.py           # 🔧 Sistema principal de testing
├── production_test.py          # 🚀 Testing avanzado con audio real
├── src/                        # Código fuente (legacy)
├── examples/                   # Audio de prueba
├── documentation/              # Documentación completa
├── requirements.txt            # Dependencias consolidadas
├── .env                        # Variables de entorno
└── venv/                       # Entorno virtual activado
```

## 🔨 Comandos de Desarrollo

### Testing Rápido
```bash
# Test sin consumir créditos (validación diaria)
./venv/Scripts/python.exe test_voiceflow.py --test

# Test completo de producción  
./venv/Scripts/python.exe test_voiceflow.py --prod

# Ejecutar aplicación principal
./venv/Scripts/python.exe main.py

# Probar servicio específico
python -c "
import asyncio
from src.voiceflow_stt_agent import VoiceflowSTTAgent
agent = VoiceflowSTTAgent.create_from_config()
print(asyncio.run(agent.health_check()))
"
```

### Desarrollo Incremental
```bash
# 1. Probar configuración
python -c "from src.factory import STTServiceFactory; print(STTServiceFactory.get_available_services())"

# 2. Verificar servicio
python -c "
from src.factory import STTServiceFactory
import os
from dotenv import load_dotenv
load_dotenv()
service = STTServiceFactory.create_from_config()
print(f'Servicio: {service.__class__.__name__}')
print(f'Disponible: {service.is_service_available()}')
"

# 3. Test completo con audio
python main.py
```

## 🧪 Testing Guidelines

### Estructura de Tests (Para Implementar)
```
tests/
├── unit/
│   ├── test_interfaces.py       # Test interfaces
│   ├── test_azure_service.py    # Test Azure STT
│   ├── test_whisper_services.py # Test Whisper STT
│   ├── test_factory.py          # Test Factory
│   └── test_agent.py            # Test Agent principal
├── integration/
│   ├── test_agent_azure.py      # Agent + Azure real
│   ├── test_agent_whisper.py    # Agent + Whisper real
│   └── test_service_switching.py # Cambio de servicios
└── e2e/
    └── test_full_flow.py        # Flujo completo con audio real
```

### Ejemplos de Tests

#### Test Unitario con Mock
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.voiceflow_stt_agent import VoiceflowSTTAgent

@pytest.mark.asyncio
async def test_agent_transcription_success():
    # Arrange
    mock_service = AsyncMock()
    mock_service.transcribe_audio.return_value = "texto transcrito"
    mock_service.is_service_available.return_value = True
    mock_service.get_service_info.return_value = {"service_name": "mock"}
    
    agent = VoiceflowSTTAgent(mock_service, "test_agent")
    
    # Act
    result = await agent.transcribe_audio("test.wav")
    
    # Assert
    assert result == "texto transcrito"
    assert len(agent.get_transcription_history()) == 1
    mock_service.transcribe_audio.assert_called_once()
```

#### Test de Integración
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_azure_service_real():
    """Test con Azure Speech real - requiere credenciales válidas"""
    # Skip si no hay credenciales
    if not (os.getenv("AZURE_SPEECH_KEY") and os.getenv("AZURE_SPEECH_REGION")):
        pytest.skip("Credenciales Azure no configuradas")
    
    # Crear servicio real
    service = STTServiceFactory.create_from_config()
    agent = VoiceflowSTTAgent(service)
    
    # Verificar health
    health = await agent.health_check()
    assert health["status"] == "healthy"
```

### Comandos de Testing
```bash
# Instalar pytest
pip install pytest pytest-asyncio pytest-mock

# Ejecutar todos los tests
pytest

# Tests específicos
pytest tests/unit/
pytest tests/integration/ -m integration
pytest -k "test_agent" -v

# Con coverage
pip install pytest-cov
pytest --cov=src --cov-report=html
```

## 🔧 Desarrollo de Nuevas Features

### 1. Agregar Nuevo Servicio STT

**Paso 1: Implementar la interfaz**
```python
# src/services/nuevo_servicio.py
from ..interfaces.stt_interface import STTServiceInterface

class NuevoServicioSTT(STTServiceInterface):
    def __init__(self, parametro_config: str):
        self.config = parametro_config
        self._initialize_service()
    
    async def transcribe_audio(self, audio_path: Path, **kwargs) -> str:
        # Tu implementación aquí
        pass
    
    def is_service_available(self) -> bool:
        # Verificar disponibilidad
        pass
    
    # ... otros métodos requeridos
```

**Paso 2: Registrar en Factory**
```python
# src/factory.py - agregar en _service_registry
_service_registry: Dict[str, Type[STTServiceInterface]] = {
    'azure': AzureSpeechService,
    'whisper_local': WhisperLocalService,
    'whisper_api': WhisperAPIService,
    'nuevo_servicio': NuevoServicioSTT,  # <-- Agregar aquí
}

# Agregar método de creación
@classmethod
def _create_nuevo_servicio(cls) -> NuevoServicioSTT:
    config = os.getenv('NUEVO_SERVICIO_CONFIG')
    return cls.create_service('nuevo_servicio', parametro_config=config)
```

**Paso 3: Actualizar configuración**
```env
# .env.example - agregar variables
NUEVO_SERVICIO_CONFIG=valor_configuracion
```

**Paso 4: Tests**
```python
# tests/unit/test_nuevo_servicio.py
def test_nuevo_servicio_creation():
    service = NuevoServicioSTT("test_config")
    assert service.is_service_available()
```

### 2. Agregar Nueva Feature al Agente

**Ejemplo: Batch Processing**
```python
# src/voiceflow_stt_agent.py
async def transcribe_batch(self, audio_paths: list[Path], **kwargs) -> list[str]:
    """Transcribe múltiples archivos en paralelo."""
    tasks = [
        self.transcribe_audio(path, **kwargs) 
        for path in audio_paths
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### 3. Mejoras de Performance

**Caching de Transcripciones:**
```python
import hashlib
from functools import lru_cache

class VoiceflowSTTAgent:
    def _get_audio_hash(self, audio_path: Path) -> str:
        """Hash del archivo para cache."""
        with open(audio_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    async def transcribe_audio_cached(self, audio_path: Path, **kwargs) -> str:
        """Transcripción con cache."""
        audio_hash = self._get_audio_hash(audio_path)
        
        # Verificar cache
        if cached := self._cache.get(audio_hash):
            return cached
        
        # Transcribir y cachear
        result = await self.transcribe_audio(audio_path, **kwargs)
        self._cache[audio_hash] = result
        return result
```

## 🔍 Debugging y Logging

### Configurar Logging Detallado
```python
import structlog
import logging

# Configuración en main.py o tests
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Usar en desarrollo
logger = structlog.get_logger(__name__)
logger.info("Debug info", extra_data="valor")
```

### Debug de Servicios STT
```python
# Verificar configuración
from src.factory import STTServiceFactory
import os

print("=== DEBUG CONFIG ===")
print(f"STT_SERVICE: {os.getenv('STT_SERVICE')}")
print(f"Servicios disponibles: {STTServiceFactory.get_available_services()}")

# Probar creación
try:
    service = STTServiceFactory.create_from_config()
    print(f"Servicio creado: {service.__class__.__name__}")
    print(f"Info: {service.get_service_info()}")
except Exception as e:
    print(f"Error: {e}")
```

### Debug de Audio
```python
from pathlib import Path

def debug_audio_file(audio_path: str):
    """Información sobre archivo de audio."""
    path = Path(audio_path)
    
    print(f"=== AUDIO DEBUG ===")
    print(f"Archivo: {path}")
    print(f"Existe: {path.exists()}")
    
    if path.exists():
        print(f"Tamaño: {path.stat().st_size / 1024:.1f} KB")
        print(f"Extensión: {path.suffix}")
        
        # Opcional: usar librosa para más info
        try:
            import librosa
            y, sr = librosa.load(str(path))
            print(f"Duración: {len(y)/sr:.1f} segundos")
            print(f"Sample rate: {sr} Hz")
        except ImportError:
            print("Instala librosa para más info: pip install librosa")

# Uso
debug_audio_file("ejemplos/audio_prueba.wav")
```

## 📦 Dependencias y Versiones

### Core Dependencies
```
azure-cognitiveservices-speech==1.34.0  # Azure STT
openai-whisper==20231117                # Whisper local
openai==1.3.0                          # Whisper API
python-dotenv==1.0.0                   # Config management
pydantic==2.5.0                        # Data validation
```

### Development Dependencies
```
pytest==7.4.3                         # Testing framework
pytest-asyncio==0.21.1               # Async tests
pytest-mock==3.12.0                  # Mocking
pytest-cov==4.0.0                    # Coverage
black==23.11.0                        # Code formatting
mypy==1.7.1                          # Type checking
```

### Instalar dependencias opcionales
```bash
# Para desarrollo completo
pip install black mypy flake8

# Para análisis de audio
pip install librosa soundfile

# Para performance profiling
pip install memory-profiler line-profiler
```

## 🚀 Deploy y Distribución

### Para PoC Local
```bash
# Crear distributable
python -m pip install build
python -m build

# O simplemente copiar carpeta src/
```

### Para Integración con Sistema Multiagente
```python
# Importar desde otro proyecto
sys.path.append('path/to/VoiceFlowPOC')
from src.voiceflow_stt_agent import VoiceflowSTTAgent

# O instalar como paquete local
pip install -e path/to/VoiceFlowPOC
```

## 🔄 Workflow de Desarrollo

### 1. Desarrollo de Feature
```bash
# 1. Crear branch
git checkout -b feature/nueva-feature

# 2. Desarrollo iterativo
# - Escribir código
# - Probar con main.py
# - Escribir tests
# - Repetir

# 3. Verificar antes de commit
python main.py
# pytest  # cuando tengas tests

# 4. Commit y push
git add .
git commit -m "feat: descripción de la feature"
git push origin feature/nueva-feature
```

### 2. Ciclo de Testing
```bash
# Testing en desarrollo
python main.py                    # Demo rápido
python -m pytest tests/unit/      # Tests unitarios
python -m pytest tests/integration/ --slow  # Tests lentos

# Testing completo antes de release
python -m pytest --cov=src       # Con coverage
mypy src/                         # Type checking
black src/ --check               # Format checking
```

### 3. Debugging Workflow
```bash
# 1. Reproducir error
python main.py 2>&1 | tee debug.log

# 2. Debug específico
python -c "
import sys
sys.path.append('src')
# ... código de debug
"

# 3. Fix y verificar
python main.py
```

---

## 📝 Convenciones de Código

### Type Hints
```python
# Siempre usar type hints
async def transcribe_audio(self, audio_path: Path, **kwargs) -> str:
    pass

# Para optional y unions
from typing import Optional, Union
def process_audio(path: Union[str, Path], config: Optional[dict] = None) -> str:
    pass
```

### Docstrings
```python
def transcribe_audio(self, audio_path: Path, **kwargs) -> str:
    """
    Transcribe un archivo de audio a texto.
    
    Args:
        audio_path: Ruta al archivo de audio
        **kwargs: Parámetros adicionales (language, etc.)
        
    Returns:
        str: Texto transcrito
        
    Raises:
        STTServiceError: Error en la transcripción
    """
    pass
```

### Error Handling
```python
# Específico y descriptivo
try:
    result = await service.transcribe_audio(path)
except FileNotFoundError:
    raise STTServiceError(f"Archivo no encontrado: {path}", "service_name")
except Exception as e:
    logger.error("Error inesperado", error=str(e))
    raise STTServiceError(f"Error transcribiendo: {e}", "service_name", e)
```
