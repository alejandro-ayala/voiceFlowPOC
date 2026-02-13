# Business Layer - Tourism Domain Module

**Estado**: Placeholder (Fase 2B pendiente)

## Propósito

Este directorio está reservado para la futura descomposición del módulo `langchain_agents.py` (Fase 2B del roadmap).

## Contenido planificado (Fase 2B)

Cuando se ejecute la descomposición del business layer, este módulo contendrá:

### Datos de dominio turístico

- **`accessibility_data.py`**: Base de datos de accesibilidad por destinos
  - `ACCESSIBILITY_DB` - Información de accesibilidad (nivel, score, facilities, certification)
  
- **`route_data.py`**: Catálogo de rutas turísticas
  - `ROUTE_DB` - Opciones de rutas con transporte, duración, accesibilidad
  
- **`venue_data.py`**: Base de datos de venues (museos, restaurantes, hoteles)
  - `VENUE_DB` - Horarios, precios, servicios de accesibilidad, contacto

### Lógica de dominio

- **`accessibility_rules.py`**: Reglas de negocio para análisis de accesibilidad
  - Algoritmos de scoring
  - Validación de certificaciones
  - Generación de recomendaciones
  
- **`domain_models.py`**: Modelos de dominio
  - `AccessibilityInfo`, `RouteInfo`, `VenueInfo` (dataclasses)
  - `TourismIntent`, `AccessibilityType` (enums)

## Referencias

- Ver [ROADMAP.md](../../documentation/ROADMAP.md#fase-1-descomposición-de-langchain_agentspy) - Fase 1, secciones 1.2-1.5
- Ver [03_business_layer_design.md](../../documentation/design/03_business_layer_design.md) - Plan de descomposición

## Estado actual

La funcionalidad de turismo actualmente reside en:
- `business/ai_agents/langchain_agents.py` - Clases:
  - `AccessibilityAnalysisTool`
  - `RoutePlanningTool`
  - `TourismInfoTool`
  
Los datos (~200 líneas de diccionarios) están inline dentro de los métodos `_run()` de cada tool.

**Acción requerida**: Ninguna hasta que se apruebe e inicie la Fase 2B.
