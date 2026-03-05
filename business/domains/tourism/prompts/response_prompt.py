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


def _build_profile_section(profile_context: dict) -> str:
    """Build the profile directives + ranking bias section for prompt injection."""
    directives = "\n".join(f"- {d}" for d in profile_context.get("prompt_directives", []))

    # Summarize ranking bias for the LLM
    bias = profile_context.get("ranking_bias", {})
    venue_types = bias.get("venue_types", {})
    sorted_types = sorted(venue_types.items(), key=lambda x: x[1], reverse=True)
    boosted = [f"{t} (x{w})" for t, w in sorted_types if w > 1.0][:3]
    penalized = [f"{t} (x{w})" for t, w in sorted_types if w < 1.0][:2]

    ranking_lines = ""
    if boosted:
        ranking_lines += f"  Preferidos: {', '.join(boosted)}\n"
    if penalized:
        ranking_lines += f"  Menos relevantes: {', '.join(penalized)}\n"

    return f"""
PERFIL DE USUARIO ACTIVO: {profile_context.get("label", "Desconocido")}
Directivas de perfil:
{directives}

Política de ranking:
{ranking_lines}
IMPORTANTE: El perfil solo afecta la PRIORIZACIÓN de resultados.\
 No filtres ni excluyas opciones válidas. Presenta todas las opciones relevantes\
 pero ordénalas y enfatízalas según las preferencias del perfil."""


def build_response_prompt(
    user_input: str,
    tool_results: dict[str, str],
    profile_context: dict | None = None,
) -> str:
    """Build the final synthesis prompt from user input and tool results.

    Args:
        user_input: Original user query text.
        tool_results: Dict with keys 'nlu', 'accessibility', 'route', 'tourism_info'.
        profile_context: Optional profile context with prompt_directives and ranking_bias.

    Returns:
        Complete prompt string for LLM invocation.
    """
    profile_section = _build_profile_section(profile_context) if profile_context else ""

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
{profile_section}
Tu respuesta debe tener DOS partes:

PARTE 1 — Texto conversacional en español:
Genera una respuesta completa y útil que incluya:
1. Recomendaciones específicas de lugares accesibles
2. Información práctica sobre rutas y transporte
3. Horarios, precios y servicios de accesibilidad
4. Consejos específicos para las necesidades del usuario
Sé conversacional, útil y enfócate en los aspectos de accesibilidad.

PARTE 2 — Bloque JSON estructurado:
Después del texto, incluye SIEMPRE un bloque de código JSON con los datos
estructurados del lugar recomendado. Usa EXACTAMENTE este formato:

```json
{TOURISM_DATA_SCHEMA}
```

Reglas para el JSON:
- SIEMPRE incluye el bloque JSON, aunque algunos campos sean null.
- Usa solo datos que conozcas con confianza. Si no estás seguro, pon null.
- facilities debe usar estos keys exactos: wheelchair_ramps,
  adapted_bathrooms, audio_guides, tactile_paths,
  sign_language_interpreters, elevator_access, wheelchair_spaces,
  hearing_loops.
- accessibility_score es un número de 0 a 10.
- Si no hay información suficiente para generar el JSON, completa con nulls.
- El bloque JSON debe estar DESPUÉS del texto conversacional."""
