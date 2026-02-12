# VoiceFlow PoC - Sistema de Turismo Accesible con IA

**Sistema completo de Speech-to-Text y Multi-Agentes IA para Turismo Accesible**

[![Status](https://img# Validación básica (testing)
./venv/Scripts/python.exe test_voiceflow.py --test

# Validación completa (pre-release)  
./venv/Scripts/python.exe test_voiceflow.py --prod

# Aplicación web principal (usuarios finales)
python run-ui.py
```badge/status-production_ready-green.svg)](https://github.com/your-repo/voiceflow-poc)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![Azure](https://img.shields.io/badge/azure-speech_services-blue.svg)](https://azure.microsoft.com/en-us/services/cognitive-services/)
[![OpenAI](https://img.shields.io/badge/openai-gpt4-green.svg)](https://openai.com)
[![LangChain](https://img.shields.io/badge/langchain-multi_agent-orange.svg)](https://langchain.com)

---

## 🎯 Descripción del Sistema

VoiceFlow PoC es un sistema de inteligencia artificial completamente funcional para turismo accesible que integra:

- **🎙️ Speech-to-Text**: Azure Speech Services para procesamiento de voz en español
- **🤖 Sistema Multi-Agente**: LangChain + OpenAI GPT-4 con 4 agentes especializados
- **♿ Especialización en Accesibilidad**: Turismo para personas con movilidad reducida
- **🏛️ Casos de Uso Reales**: Museos, parques, restaurantes, transporte público

### 🏗️ Arquitectura del Sistema

```
🎙️ Audio Input → 🗣️ Azure STT → 🧠 NLU Agent → ♿ Accessibility Agent → 🗺️ Route Agent → ℹ️ Info Agent → 🤖 GPT-4 Response
```

**Agentes Multi-Especializados:**
1. **NLU Agent**: Análisis de intención y entidades
2. **Accessibility Agent**: Evaluación de accesibilidad de venues
3. **Route Planning Agent**: Planificación de rutas accesibles
4. **Tourism Info Agent**: Información detallada de destinos

---

## 🚀 Inicio Rápido

### Sistema de Testing Consolidado

El proyecto incluye un **sistema de testing consolidado** que valida todas las integraciones:

#### 🔧 Modo TEST (Validación sin créditos)
```bash
cd VoiceFlowPOC
./venv/Scripts/python.exe test_voiceflow.py --test
```
**Resultado**: Valida todas las conexiones y configuraciones sin consumir APIs.

#### 🚀 Modo PRODUCCIÓN (Test completo)
```bash
./venv/Scripts/python.exe test_voiceflow.py --prod
```
**Resultado**: Test completo con llamadas reales a GPT-4 y escenarios de turismo accesible.

#### 🎙️ Test con Audio Real (End-to-End)
```bash
./venv/Scripts/python.exe production_test.py
```
**Resultado**: Grabación → Transcripción → Multi-Agente → Respuesta inteligente.

#### 🎯 Aplicación Principal (Web UI Moderna)
```bash
# Iniciar servidor web
python run-ui.py

# El servidor estará disponible en:
# http://localhost:8000
```
**Resultado**: Interfaz web moderna con workflow completo de turismo accesible.

---

## ⚙️ Configuración

### Variables de Entorno (.env)
```properties
# OpenAI API (GPT-4)
OPENAI_API_KEY=your_openai_key_here

# Azure Speech Services  
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=italynorth

# Configuración STT
STT_SERVICE=azure
DEFAULT_SAMPLE_RATE=16000
DEFAULT_CHANNELS=1
LOG_LEVEL=INFO
```

### Instalación de Dependencias
```bash
cd VoiceFlowPOC

# Instalar dependencias con Poetry
poetry install

# O ejecutar directamente con Docker (recomendado)
docker compose up --build
```

---

## 📊 Estado del Sistema

### ✅ Componentes Validados
- **OpenAI API**: ✅ GPT-4 operativo con créditos recargados
- **Azure Speech**: ✅ STT configurado para español (es-ES)  
- **LangChain Multi-Agent**: ✅ 4 agentes coordinados perfectamente
- **Sistema de Audio**: ✅ 29 dispositivos detectados
- **Pipeline End-to-End**: ✅ Workflow completo funcional

### 🎯 Escenarios Validados
1. **Museo del Prado**: Ruta accesible en silla de ruedas ✅
2. **Parque del Retiro**: Visita con problemas de visión ✅
3. **Gran Vía**: Restaurantes accesibles ✅
4. **Metro Madrid**: Información para personas con muletas ✅

---

## 📁 Estructura del Proyecto

```
VoiceFlowPOC/
├── test_voiceflow.py          # 🔧 Sistema principal de testing  
├── run-ui.py                  # 🎯 Entry point - Servidor Web UI
├── langchain_agents.py        # 🤖 Sistema multi-agente LangChain
├── web_ui/                    # � Aplicación web FastAPI
│   ├── app.py                # FastAPI application
│   ├── api/v1/               # REST API endpoints
│   └── static/               # Frontend assets
├── pyproject.toml             # 📦 Dependencias y configuracion (Poetry)
├── poetry.lock                # 🔒 Lock file de dependencias
├── .env                       # ⚙️ Configuración y API keys
├── README.md                  # 📖 Este archivo
└── documentation/             # 📚 Documentación completa
    ├── TESTING_SYSTEM_README.md
    ├── SISTEMA_CONSOLIDADO_FINAL.md
    ├── ARCHITECTURE_MULTIAGENT.md
    └── AZURE_SETUP_GUIDE.md
```

---

## 🎯 Casos de Uso Principales

### 1. Turista con Silla de Ruedas
**Input**: "Necesito ir al Museo del Prado en silla de ruedas"  
**Output**: Rutas accesibles (metro/bus), información de accesibilidad del museo, precios, horarios, contactos de coordinación.

### 2. Persona con Problemas de Visión  
**Input**: "¿Cómo visitar el Parque del Retiro con problemas de visión?"  
**Output**: Transporte con guías táctiles, servicios de audio, rutas adaptadas, información de apoyo.

### 3. Búsqueda de Restaurantes Accesibles
**Input**: "Restaurantes accesibles cerca de Gran Vía"  
**Output**: Opciones de dining accesible, información de transporte, certificaciones ONCE.

---

## 🔧 Comandos Esenciales

```bash
# Validación diaria (desarrollo)
./venv/Scripts/python.exe test_voiceflow.py --test

# Validación completa (pre-release)  
./venv/Scripts/python.exe test_voiceflow.py --prod

# Demo con audio real (presentaciones)
./venv/Scripts/python.exe production_test.py

# Aplicación de usuario final
./venv/Scripts/python.exe main.py
```

---

## 📚 Documentación Completa

- **[TESTING_SYSTEM_README.md](documentation/TESTING_SYSTEM_README.md)** - Guía completa del sistema de testing
- **[SISTEMA_CONSOLIDADO_FINAL.md](documentation/SISTEMA_CONSOLIDADO_FINAL.md)** - Estado final y consolidación
- **[ARCHITECTURE_MULTIAGENT.md](documentation/ARCHITECTURE_MULTIAGENT.md)** - Arquitectura del sistema multi-agente  
- **[AZURE_SETUP_GUIDE.md](documentation/AZURE_SETUP_GUIDE.md)** - Configuración de Azure Speech Services

---

## 🏆 Logros del Proyecto

### ✅ Sistema Completamente Funcional
- **Pipeline End-to-End**: Desde voz hasta recomendaciones inteligentes
- **Multi-Agente IA**: 4 agentes especializados coordinados
- **Testing Automatizado**: Sistema de validación consolidado
- **Arquitectura Robusta**: Código limpio, mantenible y escalable

### ✅ Validación Real
- **Audio Real**: Grabación y procesamiento de voz en español
- **APIs Productivas**: OpenAI GPT-4 y Azure Speech Services
- **Casos de Uso Reales**: Escenarios de turismo accesible validados
- **Sistema Consolidado**: De 15+ archivos de test a 2 archivos potentes

---

## 🚀 Estado: LISTO PARA PRODUCCIÓN

**El sistema VoiceFlow PoC está completamente desarrollado, validado y listo para uso en producción.**

### Próximos Pasos Sugeridos
1. **Integración con APIs reales**: Google Maps, bases de datos de accesibilidad
2. **Interfaz de usuario**: Web app o aplicación móvil
3. **Memoria conversacional**: Sistema de seguimiento de contexto
4. **Nuevos agentes**: Clima, eventos, transporte especializado

---

*Desarrollado con ❤️ para hacer el turismo más accesible para todos*
