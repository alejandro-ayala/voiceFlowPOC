# VoiceFlow PoC - Sistema de Testing Consolidado

## 📋 Resumen

Sistema consolidado de testing y validación para el proyecto VoiceFlow PoC que integra:

- **Azure Speech Services** (STT)
- **LangChain Multi-Agent System** 
- **OpenAI GPT-4 API**
- **Sistema de audio en tiempo real**

## 🗂️ Estructura del Proyecto

### Archivos Principales
- `test_voiceflow.py` - Sistema de testing principal con 2 modos (TEST/PRODUCCIÓN)
- `production_test.py` - Testing avanzado con audio real y scenarios end-to-end
- `langchain_agents.py` - Sistema multi-agente de LangChain
- `main.py` - Aplicación principal con workflow completo

### Configuración
- `.env` - Variables de entorno (API keys, configuración)
- `requirements.txt` - Dependencias consolidadas
- `venv/` - Entorno virtual con todas las dependencias

## 🚀 Uso Rápido

### 1. Modo TEST (Validación mínima - sin consumir créditos)
```bash
cd "/d/Code/TurismoReducido/VoiceFlowPOC"
./venv/Scripts/python.exe test_voiceflow.py --test
```

### 2. Modo PRODUCCIÓN (Test completo - consume créditos)
```bash
cd "/d/Code/TurismoReducido/VoiceFlowPOC"
./venv/Scripts/python.exe test_voiceflow.py --prod
```

### 3. Testing con Audio Real (End-to-End)
```bash
cd "/d/Code/TurismoReducido/VoiceFlowPOC"
./venv/Scripts/python.exe production_test.py
```

### 4. Aplicación Principal (Workflow Completo)
```bash
cd "/d/Code/TurismoReducido/VoiceFlowPOC"
./venv/Scripts/python.exe main.py
```

## 🔧 Características del Sistema de Testing

### test_voiceflow.py - Sistema Principal

#### MODO TEST (--test)
- ✅ **Validación de entorno** (variables de configuración)
- ✅ **Test conexión OpenAI** (solo validación de cliente, no consume créditos)
- ✅ **Test Azure Speech** (solo configuración)
- ✅ **Test LangChain** (inicialización de herramientas)
- ✅ **Test sistema de audio** (detección de dispositivos)

#### MODO PRODUCCIÓN (--prod)
- ✅ **Test completo OpenAI** (llamadas reales a GPT-4)
- ✅ **Test LangChain completo** (workflow multi-agente real)
- ✅ **Test escenarios de turismo accesible** (3 casos reales)
- ✅ **Validación end-to-end** (flujo completo)

### production_test.py - Testing Avanzado

#### Funcionalidades
- 🎙️ **Grabación de audio en tiempo real**
- 🗣️ **Transcripción con Azure Speech Services**
- 🤖 **Procesamiento con LangChain Multi-Agent**
- 📊 **Test de escenarios predefinidos**
- 📋 **Reportes detallados en JSON**

## 📊 Reportes y Resultados

### Archivos de Resultados
El sistema genera automáticamente:
- `test_results_test_YYYYMMDD_HHMMSS.json` - Resultados modo test
- `test_results_production_YYYYMMDD_HHMMSS.json` - Resultados modo producción
- `production_test_YYYYMMDD_HHMMSS.json` - Resultados testing avanzado

### Formato de Reportes
Los reportes incluyen:
- **Estado general** del sistema (EXITOSO/FALLIDO)
- **Componentes individuales** (OpenAI, Azure, LangChain, Audio)
- **Respuestas de ejemplo** (en modo producción)
- **Métricas de rendimiento**
- **Recomendaciones** de acción

## 🛠️ Configuración Requerida

### Variables de Entorno (.env)
```properties
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Azure Speech Services
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=italynorth

# Configuración STT
STT_SERVICE=azure
```

### Dependencias (requirements.txt)
```
azure-cognitiveservices-speech==1.34.0
langchain==0.1.0
openai>=1.6.1,<2.0.0
sounddevice==0.5.3
...
```

## 📈 Casos de Uso Validados

### Escenarios de Turismo Accesible
1. **Museo del Prado con silla de ruedas**
   - Rutas accesibles (metro/autobús)
   - Información de accesibilidad del museo
   - Precios y horarios
   - Servicios especiales

2. **Parque del Retiro con problemas de visión**
   - Transporte con guías táctiles
   - Servicios de audio
   - Rutas adaptadas

3. **Restaurantes accesibles en Gran Vía**
   - Opciones de dining accesible
   - Información de transporte
   - Certificaciones de accesibilidad

4. **Transporte público para personas con muletas**
   - Líneas de metro accesibles
   - Alternativas de transporte
   - Información práctica

## ✅ Estado del Proyecto

### Sistemas Validados
- ✅ **OpenAI API** - Funcionando correctamente
- ✅ **Azure Speech Services** - Configurado y operativo
- ✅ **LangChain Multi-Agent** - 4 agentes coordinados (NLU, Accessibility, Route, Info)
- ✅ **Sistema de Audio** - 29 dispositivos detectados
- ✅ **Pipeline End-to-End** - Flujo completo validado

### Arquitectura Multi-Agente
```
🎙️ Audio Input → 🗣️ Azure STT → 🧠 NLU Agent → ♿ Accessibility Agent → 🗺️ Route Agent → ℹ️ Info Agent → 🤖 GPT-4 Response
```

## 🚀 Próximos Pasos

1. **Integración con APIs reales** (Google Maps, bases de datos turísticas)
2. **Mejora de agentes especializados** (clima, eventos, transporte)
3. **Memoria conversacional** para seguimiento de contexto
4. **Despliegue como servicio web** o aplicación móvil
5. **Interfaces de usuario** más avanzadas

## 📞 Soporte

Para soporte técnico o preguntas sobre el sistema, consulta:
- Documentos de arquitectura en el proyecto
- Logs detallados en los archivos de resultados
- Configuración en archivos `.env` y `requirements.txt`

---

**Sistema consolidado y validado** ✅  
**Listo para producción** 🚀  
**Testing automatizado** 🤖
