# VoiceFlow STT Agent - Prueba de Concepto

Este proyecto implementa un agente de Speech-to-Text (STT) como parte de un sistema multiagente para planificación de rutas de ocio accesibles.

## 🏗️ Arquitectura

El proyecto sigue los principios SOLID y está diseñado para ser:
- **Escalable**: Fácil agregar nuevos servicios STT
- **Testeable**: Interfaces bien definidas para mocking
- **Configurable**: Sin necesidad de modificar código
- **Modular**: Separación clara de responsabilidades

### Estructura del Proyecto

```
src/
├── interfaces/
│   └── stt_interface.py      # Interfaz base para servicios STT
├── services/
│   ├── azure_speech_service.py   # Implementación Azure Speech
│   └── whisper_services.py       # Implementaciones Whisper (local y API)
├── factory.py                # Factory para crear servicios STT
└── voiceflow_stt_agent.py   # Agente principal STT
```

## ⚙️ Configuración

1. **Copiar archivo de configuración:**
   ```bash
   cp .env.example .env
   ```

2. **Configurar variables de entorno en `.env`:**

   ### Para Azure Speech Services:
   ```env
   STT_SERVICE=azure
   AZURE_SPEECH_KEY=tu_clave_azure
   AZURE_SPEECH_REGION=tu_region_azure
   ```

   ### Para Whisper Local:
   ```env
   STT_SERVICE=whisper_local
   WHISPER_MODEL=base
   ```

   ### Para Whisper API:
   ```env
   STT_SERVICE=whisper_api
   OPENAI_API_KEY=tu_clave_openai
   ```

## 🚀 Instalación

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Para usar Azure Speech (recomendado para PoC):**
   ```bash
   pip install azure-cognitiveservices-speech
   ```

3. **Para usar Whisper local:**
   ```bash
   pip install openai-whisper
   ```

4. **Para usar Whisper API:**
   ```bash
   pip install openai
   ```

## 📋 Servicios STT Disponibles

### 1. Azure Speech Services (Recomendado)
- ✅ **Ideal para PoC universitaria**
- ✅ Tier gratuito: 5 horas/mes
- ✅ Créditos Azure for Students suficientes
- ✅ Muy preciso
- ✅ Soporta múltiples idiomas

### 2. OpenAI Whisper Local
- ✅ **Completamente gratuito**
- ✅ Funciona offline
- ✅ Muy preciso
- ⚠️ Requiere recursos computacionales

### 3. OpenAI Whisper API
- ✅ Muy preciso
- ✅ No requiere recursos locales
- ⚠️ Costo: ~$0.006 por minuto

## 📁 Formatos de Audio Soportados

- **WAV** (recomendado para máxima calidad)
- **MP3**
- **M4A**
- **FLAC**
- **OGG**
- **WEBM** (solo Whisper)

## 🎯 Uso Básico

```python
import asyncio
from src.voiceflow_stt_agent import VoiceflowSTTAgent

async def main():
    # Crear agente desde configuración
    agent = VoiceflowSTTAgent.create_from_config()
    
    # Verificar estado del agente
    health = await agent.health_check()
    print(f"Estado del agente: {health['status']}")
    
    # Transcribir audio
    transcription = await agent.transcribe_audio("path/to/audio.wav")
    print(f"Transcripción: {transcription}")
    
    # Obtener información del servicio
    info = agent.get_service_info()
    print(f"Servicio: {info['service_info']['service_name']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔧 Extensibilidad

### Agregar un Nuevo Servicio STT

1. **Crear clase que implemente `STTServiceInterface`:**
   ```python
   from src.interfaces.stt_interface import STTServiceInterface
   
   class MiNuevoServicioSTT(STTServiceInterface):
       # Implementar métodos abstractos
       pass
   ```

2. **Registrar en el factory:**
   ```python
   from src.factory import STTServiceFactory
   
   STTServiceFactory.register_service("mi_servicio", MiNuevoServicioSTT)
   ```

## 🧪 Testing

La arquitectura permite fácil testing mediante mocking:

```python
import pytest
from unittest.mock import AsyncMock
from src.voiceflow_stt_agent import VoiceflowSTTAgent

@pytest.mark.asyncio
async def test_transcription():
    # Mock del servicio STT
    mock_service = AsyncMock()
    mock_service.transcribe_audio.return_value = "Texto transcrito"
    mock_service.is_service_available.return_value = True
    
    # Crear agente con mock
    agent = VoiceflowSTTAgent(mock_service)
    
    # Probar transcripción
    result = await agent.transcribe_audio("test.wav")
    assert result == "Texto transcrito"
```

## 📊 Monitoreo y Debugging

El agente mantiene historial de transcripciones:

```python
# Obtener historial
history = agent.get_transcription_history()

# Ver estadísticas
info = agent.get_service_info()
print(f"Transcripciones realizadas: {info['transcription_count']}")
```

## 🔍 Troubleshooting

### Error: "Import could not be resolved"
- Los errores de import son normales hasta instalar las dependencias
- Ejecuta: `pip install -r requirements.txt`

### Error: "Servicio STT no está disponible"
- Verifica las variables de entorno en `.env`
- Para Azure: confirma `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION`
- Para OpenAI: confirma `OPENAI_API_KEY`

### Error: "Formato de audio no soportado"
- Convierte el audio a WAV 16kHz mono para mejor compatibilidad
- Usa herramientas como FFmpeg para conversión

## � Documentación Adicional

Para desarrolladores y futuros mantenedores del proyecto:

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Decisiones de arquitectura, patrones SOLID, y contexto técnico detallado
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Guía completa de desarrollo, testing, y workflows
- **[API_REFERENCE.md](API_REFERENCE.md)** - Documentación completa de todas las clases, métodos y ejemplos de uso

## �📈 Próximos Pasos

1. **Integración con Sistema Multiagente**
2. **Optimización de performance**
3. **Manejo de audio en tiempo real** 
4. **Métricas avanzadas y logging**
5. **Interfaz web para testing**

---

## 🤝 Contribución

Para agregar nuevas funcionalidades:
1. Mantén los principios SOLID (ver [ARCHITECTURE.md](ARCHITECTURE.md))
2. Implementa tests unitarios (ver [DEVELOPMENT.md](DEVELOPMENT.md))
3. Actualiza la documentación correspondiente
4. Usa type hints y docstrings (ver [API_REFERENCE.md](API_REFERENCE.md))
