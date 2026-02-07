# Documentacion del Proyecto - VoiceFlow Tourism PoC

**Actualizado**: 4 de Febrero de 2026

---

## Documentacion principal

### Para empezar
- **[QUICK_START.md](QUICK_START.md)** - Setup en 5 minutos y primeros pasos
- **[AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md)** - Configuracion de Azure Speech Services
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Guia completa de desarrollo

### Arquitectura y diseno
- **[INFORME_FINAL_ARQUITECTONICO.md](../INFORME_FINAL_ARQUITECTONICO.md)** - Estado general de la arquitectura (4 capas)
- **[ARCHITECTURE_MULTIAGENT.md](ARCHITECTURE_MULTIAGENT.md)** - Diseno del sistema multi-agente LangChain + STT
- **[API_REFERENCE.md](API_REFERENCE.md)** - Referencia de endpoints REST, interfaces y servicios STT

### Documentos de diseno por capa (SDDs)
- **[01_shared_layer_design.md](design/01_shared_layer_design.md)** - Interfaces, excepciones, DI
- **[02_integration_layer_design.md](design/02_integration_layer_design.md)** - STT services, settings, persistencia
- **[03_business_layer_design.md](design/03_business_layer_design.md)** - LangChain multi-agent
- **[04_application_layer_design.md](design/04_application_layer_design.md)** - API endpoints, servicios, orquestacion
- **[05_presentation_layer_design.md](design/05_presentation_layer_design.md)** - FastAPI factory, templates, frontend

### Evolucion del proyecto
- **[ROADMAP.md](ROADMAP.md)** - Plan de accion: refactor, Docker, testing, persistencia, CI/CD

### Recursos adicionales
- **[Viability_Analysis_Iteration_2.pdf](Viability_Analysis_Iteration_2.pdf)** - Analisis de viabilidad del proyecto

---

## Por audiencia

| Audiencia | Documentos recomendados |
|-----------|------------------------|
| **Nuevo en el proyecto** | QUICK_START -> DEVELOPMENT -> ARCHITECTURE_MULTIAGENT |
| **Desarrollador** | DEVELOPMENT -> API_REFERENCE -> SDDs (design/) -> ROADMAP |
| **Arquitecto** | INFORME_FINAL -> SDDs (design/) -> ROADMAP -> ARCHITECTURE_MULTIAGENT |
| **Project Manager** | INFORME_FINAL -> ROADMAP -> Viability Analysis PDF |

## Por caso de uso

| Necesito... | Documento |
|-------------|-----------|
| Arrancar la app rapidamente | [QUICK_START.md](QUICK_START.md) |
| Configurar Azure Speech | [AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md) |
| Entender la arquitectura | [INFORME_FINAL_ARQUITECTONICO.md](../INFORME_FINAL_ARQUITECTONICO.md) |
| Ver los endpoints disponibles | [API_REFERENCE.md](API_REFERENCE.md) |
| Entender una capa especifica | [design/](design/) (SDDs 01-05) |
| Saber que viene despues | [ROADMAP.md](ROADMAP.md) |
| Agregar un nuevo servicio STT | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Entender el multi-agente | [ARCHITECTURE_MULTIAGENT.md](ARCHITECTURE_MULTIAGENT.md) |
