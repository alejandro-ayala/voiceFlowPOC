# Business Layer - NLP Module

**Estado**: Placeholder (Fase 2B pendiente)

## Propósito

Este directorio está reservado para la futura descomposición del módulo `langchain_agents.py` (Fase 2B del roadmap).

## Contenido planificado (Fase 2B)

Cuando se ejecute la descomposición del business layer, este módulo contendrá:

- **Patrones de NLU**: Patrones de extracción para análisis de lenguaje natural
  - `nlu_patterns.py` - `INTENT_PATTERNS`, `DESTINATION_PATTERNS`, `ACCESSIBILITY_PATTERNS`
  
- **Modelos de dominio**: Estructuras de datos para intenciones y entidades
  - `intent_models.py` - Enums y dataclasses para intenciones turísticas
  - `entity_extractors.py` - Lógica de extracción de entidades (destinos, necesidades accesibilidad)

## Referencias

- Ver [ROADMAP.md](../../documentation/ROADMAP.md#fase-1-descomposición-de-langchain_agentspy) - Fase 1, sección 1.2
- Ver [03_business_layer_design.md](../../documentation/design/03_business_layer_design.md) - Plan de descomposición

## Estado actual

La funcionalidad NLU actualmente reside en:
- `business/ai_agents/langchain_agents.py` - Clase `TourismNLUTool`

**Acción requerida**: Ninguna hasta que se apruebe e inicie la Fase 2B.
