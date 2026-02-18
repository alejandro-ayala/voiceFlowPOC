"""Response prompt builder for the tourism domain."""

TOURISM_DATA_SCHEMA = """{
  "routes": [
    {
      "transport": "metro | bus | walking | taxi",
      "line": "string | null",
      "duration": "string",
      "accessibility": "full | partial",
      "cost": "string | null",
      "steps": ["string"]
    }
  ],
  "accessibility": {
    "level": "full_wheelchair_access | partial_wheelchair_access | varies_by_location",
    "score": 0-10,
    "certification": "string | null",
    "facilities": ["string"],
    "services": {"key": "value"}
  }
}"""


def build_response_prompt(user_input: str, tool_results: dict[str, str]) -> str:
    """Build the final synthesis prompt from user input and tool results.

    Args:
        user_input: Original user query text.
        tool_results: Dict with keys 'nlu', 'accessibility', 'route', 'tourism_info'.

    Returns:
        Complete prompt string for LLM invocation.
    """
    return f"""Eres un asistente experto en turismo accesible en España.

El usuario preguntó: "{user_input}"

He analizado su consulta usando varias herramientas especializadas:

ANÁLISIS DE INTENCIÓN:
{tool_results.get("nlu", "{}")}

ANÁLISIS DE ACCESIBILIDAD:
{tool_results.get("accessibility", "{}")}

PLANIFICACIÓN DE RUTAS:
{tool_results.get("route", "{}")}

INFORMACIÓN TURÍSTICA:
{tool_results.get("tourism_info", "{}")}

Tu respuesta debe tener DOS partes:

PARTE 1 — Texto conversacional en español:
Genera una respuesta completa y útil que incluya:
1. Recomendaciones específicas de lugares accesibles
2. Información práctica sobre rutas y transporte
3. Horarios, precios y servicios de accesibilidad
4. Consejos específicos para las necesidades del usuario
Sé conversacional, útil y enfócate en los aspectos de accesibilidad.

PARTE 2 — Bloque JSON estructurado:
Después del texto, incluye un bloque de código JSON con los datos
estructurados del lugar recomendado. Usa EXACTAMENTE este formato:

```json
{TOURISM_DATA_SCHEMA}
```

Reglas para el JSON:
- Usa solo datos que conozcas con confianza. Si no estás seguro, pon null.
- facilities debe usar estos keys exactos: wheelchair_ramps,
  adapted_bathrooms, audio_guides, tactile_paths,
  sign_language_interpreters, elevator_access, wheelchair_spaces,
  hearing_loops.
- accessibility_score es un número de 0 a 10.
- Si no hay información suficiente para generar el JSON, omite el bloque.
- El bloque JSON debe estar DESPUÉS del texto conversacional."""
