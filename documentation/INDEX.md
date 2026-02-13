# Documentacion del Proyecto - VoiceFlow Tourism PoC

**Actualizado**: 12 de Febrero de 2026

---

## Documentacion principal

### Para empezar
- **[QUICK_START.md](QUICK_START.md)** - Setup en 5 minutos y primeros pasos
- **[AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md)** - Configuracion de Azure Speech Services
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Guia completa de desarrollo
- **[../docker/README.md](../docker/README.md)** - Docker: desarrollo, produccion y deployment

### Arquitectura y diseno
- **[ARCHITECTURE_VOICE-FLOW-POC.md](ARCHITECTURE_VOICE-FLOW-POC.md)** - Informe arquitectonico completo (4 capas + Docker)
- **[ARCHITECTURE_MULTIAGENT.md](ARCHITECTURE_MULTIAGENT.md)** - Diseno del sistema multi-agente LangChain + STT
- **[API_REFERENCE.md](API_REFERENCE.md)** - Referencia de endpoints REST, interfaces y servicios STT

### Documentos de diseno por capa (SDDs)
- **[01_shared_layer_design.md](design/01_shared_layer_design.md)** - Interfaces, excepciones, DI
- **[02_integration_layer_design.md](design/02_integration_layer_design.md)** - STT services, settings, persistencia
- **[03_business_layer_design.md](design/03_business_layer_design.md)** - LangChain multi-agent
- **[04_application_layer_design.md](design/04_application_layer_design.md)** - API endpoints, servicios, orquestacion
- **[05_presentation_layer_design.md](design/05_presentation_layer_design.md)** - FastAPI factory, templates, frontend

### Operaciones y seguridad
- **[SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md)** - Gestion de credenciales (git-crypt + GitHub Secrets)

### Evolucion del proyecto
- **[ROADMAP.md](ROADMAP.md)** - Plan de accion completo: testing, CI/CD, persistencia, monitoring

### Recursos adicionales
- **[Viability_Analysis_Iteration_2.pdf](Viability_Analysis_Iteration_2.pdf)** - Analisis de viabilidad del proyecto

---

## Por audiencia

| Audiencia | Documentos recomendados |
|-----------|------------------------|
| **Nuevo en el proyecto** | QUICK_START -> docker/README.md -> DEVELOPMENT |
| **Desarrollador** | DEVELOPMENT -> docker/README.md -> API_REFERENCE -> SDDs |
| **Arquitecto** | ARCHITECTURE_VOICE-FLOW-POC -> SDDs -> ROADMAP |
| **DevOps/SRE** | docker/README.md -> ROADMAP (Fase 5: CI/CD) |
| **Project Manager** | ARCHITECTURE_VOICE-FLOW-POC -> ROADMAP |

## Por caso de uso

| Necesito... | Documento |
|-------------|-----------|
| Usar Docker (desarrollo) | [../docker/README.md](../docker/README.md) |
| Deploy con Docker (produccion) | [../docker/README.md](../docker/README.md) + [ROADMAP Fase 5](ROADMAP.md) |
| Configurar Azure Speech | [AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md) |
| Entender la arquitectura | [ARCHITECTURE_VOICE-FLOW-POC.md](ARCHITECTURE_VOICE-FLOW-POC.md) |
| Ver los endpoints disponibles | [API_REFERENCE.md](API_REFERENCE.md) |
| Entender una capa especifica | [design/](design/) (SDDs 01-05) |
| Saber que viene despues | [ROADMAP.md](ROADMAP.md) |
| Setup CI/CD | [ROADMAP.md](ROADMAP.md) (Fase 5) |
| Gestionar secrets/credenciales | [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md) |
| Agregar un nuevo servicio STT | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Entender el multi-agente | [ARCHITECTURE_MULTIAGENT.md](ARCHITECTURE_MULTIAGENT.md) |
