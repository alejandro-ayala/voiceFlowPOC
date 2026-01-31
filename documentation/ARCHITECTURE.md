# Arquitectura del VoiceflowSTTAgent

## 📋 Contexto del Proyecto

Este proyecto implementa un **Agente de Speech-to-Text (STT)** como parte de un sistema multiagente para planificación de rutas de ocio accesibles. Es una Prueba de Concepto (PoC) desarrollada por un Ingeniero de Software para un proyecto de impacto social enfocado en accesibilidad.

### Objetivo Principal
Crear el core de un agente STT escalable que pueda:
- Recibir archivos de audio (simulando entrada de voz)
- Devolver texto transcrito para el sistema multiagente posterior
- Permitir fácil intercambio entre diferentes servicios STT

## 🏗️ Decisiones de Arquitectura

### Principios SOLID Aplicados

#### 1. Single Responsibility Principle (SRP)
- **`STTServiceInterface`**: Solo define el contrato para servicios STT
- **`AzureSpeechService`**: Solo maneja Azure Cognitive Services Speech
- **`WhisperLocalService`**: Solo maneja Whisper en local
- **`WhisperAPIService`**: Solo maneja Whisper via API
- **`VoiceflowSTTAgent`**: Solo coordina transcripciones, no implementa STT
- **`STTServiceFactory`**: Solo crea instancias de servicios STT

#### 2. Open/Closed Principle (OCP)
- **Extensible**: Nuevos servicios STT se agregan implementando `STTServiceInterface`
- **Cerrado**: No necesitas modificar código existente para agregar servicios
- **Factory Pattern**: `STTServiceFactory` permite registrar nuevos servicios dinámicamente

```python
# Agregar nuevo servicio sin tocar código existente
STTServiceFactory.register_service("nuevo_servicio", NuevoServicioSTT)
```

#### 3. Liskov Substitution Principle (LSP)
Todos los servicios STT son intercambiables:
```python
# Cualquier implementación funciona igual
service: STTServiceInterface = AzureSpeechService(key, region)
service: STTServiceInterface = WhisperLocalService(model)
agent = VoiceflowSTTAgent(service)  # Mismo comportamiento
```

#### 4. Interface Segregation Principle (ISP)
- `STTServiceInterface` solo define métodos esenciales para STT
- No fuerza implementaciones innecesarias

#### 5. Dependency Inversion Principle (DIP)
- `VoiceflowSTTAgent` depende de `STTServiceInterface` (abstracción)
- No depende de implementaciones concretas (Azure, Whisper, etc.)
- Permite inyección de dependencias y testing fácil

### Patrones de Diseño Implementados

#### Factory Pattern
- **Clase**: `STTServiceFactory`
- **Propósito**: Crear servicios STT basados en configuración
- **Ventajas**: 
  - Configuración centralizada
  - Fácil testing con diferentes servicios
  - Ocultación de lógica de creación

#### Strategy Pattern (Implícito)
- **Implementación**: Via `STTServiceInterface`
- **Propósito**: Intercambiar algoritmos STT en runtime
- **Ventajas**: 
  - Cambio de servicio sin modificar código
  - Fácil A/B testing de servicios

## 🎯 Servicios STT - Análisis y Decisiones

### 1. Azure Speech Services (Recomendado para PoC)

**¿Por qué Azure sobre Voiceflow?**
- **Voiceflow** está orientado a conversational AI/chatbots, no STT puro
- **Azure Speech** es específico para transcripción, más eficiente
- **Créditos universitarios** cubren perfectamente la PoC
- **Tier gratuito**: 5 horas/mes, ideal para desarrollo

**Configuración:**
```env
STT_SERVICE=azure
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=eastus
```

**Ventajas técnicas:**
- ✅ Enterprise-ready
- ✅ Soporte multiidioma robusto
- ✅ Manejo automático de formatos de audio
- ✅ Excelente precisión

### 2. OpenAI Whisper Local

**¿Cuándo usar?**
- Desarrollo sin costos
- Requisitos de privacidad (datos no salen del servidor)
- Control total sobre el modelo

**Modelos disponibles:**
- `tiny`: Más rápido, menos preciso
- `base`: Balance recomendado para PoC
- `large-v3`: Máxima precisión, más recursos

**Configuración:**
```env
STT_SERVICE=whisper_local
WHISPER_MODEL=base
```

### 3. OpenAI Whisper API

**¿Cuándo usar?**
- Máxima precisión requerida
- Sin recursos computacionales locales
- Escalabilidad inmediata

**Limitaciones:**
- 25MB máximo por archivo
- Costo por uso ($0.006/minuto)

## 🔧 Arquitectura de Configuración

### Configuración Sin Código
Todo el comportamiento se controla via `.env`:

```env
# Cambiar servicio completo
STT_SERVICE=azure  # o whisper_local, whisper_api

# Parámetros específicos por servicio
AZURE_SPEECH_KEY=...
WHISPER_MODEL=base
OPENAI_API_KEY=...

# Configuración de audio
SUPPORTED_FORMATS=wav,mp3,m4a,flac,ogg
DEFAULT_SAMPLE_RATE=16000
```

### Flujo de Inicialización

1. **Factory lee `.env`** → Determina servicio a usar
2. **Factory crea servicio** → Con parámetros específicos
3. **Agente recibe servicio** → Via dependency injection
4. **Agente listo** → Para transcripciones

## 🚀 Escalabilidad Futura

### Preparado para Sistema Multiagente

**Diseño asíncrono:**
```python
# Múltiples transcripciones concurrentes (futuro)
tasks = [agent.transcribe_audio(f) for f in audio_files]
results = await asyncio.gather(*tasks)
```

**Health checks integrados:**
```python
# Monitoreo automático del agente
health = await agent.health_check()
if health['status'] != 'healthy':
    # Failover a otro agente o servicio
```

**Historial y métricas:**
```python
# Auditoría completa
history = agent.get_transcription_history()
# Análisis de performance, errores, etc.
```

### Extensiones Planificadas

1. **Streaming STT**: Para audio en tiempo real
2. **Batch Processing**: Múltiples archivos simultáneos
3. **Fallback Services**: Si un servicio falla, usar otro
4. **Cache de Transcripciones**: Evitar re-procesar mismo audio
5. **Métricas Avanzadas**: Latencia, precisión, costos

## 🧪 Filosofía de Testing

### Inyección de Dependencias
```python
# Test con mock
mock_service = AsyncMock()
agent = VoiceflowSTTAgent(mock_service)

# Test con servicio real
real_service = AzureSpeechService(key, region)
agent = VoiceflowSTTAgent(real_service)
```

### Tests por Capa
- **Unit Tests**: Cada servicio STT por separado
- **Integration Tests**: Agent + servicio real 
- **E2E Tests**: Flujo completo con archivos reales

## 📊 Consideraciones de Performance

### Formato de Audio Óptimo
- **WAV 16kHz mono**: Mejor balance calidad/performance
- **Compresión**: MP3/M4A aceptables, conversión automática
- **Tamaño**: Azure sin límite, Whisper API 25MB máx

### Memory Management
- **Whisper Local**: Modelo se carga una vez, reutiliza
- **API Services**: Sin carga de memoria local
- **Async**: No bloquea durante transcripción

## 🔐 Seguridad y Credenciales

### Manejo de API Keys
- **Nunca en código**: Solo en variables de entorno
- **Validación**: Factory verifica credenciales antes de crear servicios
- **Error Handling**: Mensajes informativos sin exponer keys

### Datos de Audio
- **Local Processing**: Whisper local, datos no salen del servidor
- **Cloud Services**: Azure/OpenAI, revisar políticas de privacidad
- **Temporal Files**: No se almacenan transcripciones por defecto

## 🚨 Manejo de Errores

### Jerarquía de Excepciones
```python
STTServiceError                    # Base
├── AudioFormatError              # Formato no soportado
├── ServiceConfigurationError     # Configuración incorrecta
└── [Extensibles]                 # Nuevos tipos según necesidad
```

### Recovery Strategies
1. **Validation Early**: Verificar archivos antes de enviar
2. **Graceful Degradation**: Fallback a otros servicios
3. **Detailed Logging**: Para debugging y monitoreo
4. **User-Friendly Messages**: Sin detalles técnicos internos

---

## 📝 Notas para Futuros Desarrolladores

### Al Agregar Nuevos Servicios STT:
1. Implementar `STTServiceInterface`
2. Manejar errores con excepciones apropiadas
3. Actualizar `STTServiceFactory` si necesario
4. Agregar tests unitarios
5. Documentar configuración en README.md

### Al Modificar Interfaces:
1. Mantener backward compatibility
2. Actualizar todas las implementaciones
3. Versionar cambios breaking
4. Comunicar cambios al equipo

### Al Integrar con Sistema Multiagente:
1. Usar `health_check()` para monitoreo
2. Implementar retry logic en fallos
3. Considerar load balancing entre agentes
4. Métricas de performance para SLA
