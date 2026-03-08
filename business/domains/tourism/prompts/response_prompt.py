"""Response prompt builder for the tourism domain."""


def _tool_value(tool_results: dict[str, str], *keys: str) -> str:
  """Return first non-empty tool payload among candidate keys."""
  for key in keys:
    value = tool_results.get(key)
    if isinstance(value, str) and value.strip():
      return value
  return "{}"


def _build_additional_tools_section(tool_results: dict[str, str]) -> str:
  """Render additional tool outputs that are not part of the main fixed sections."""
  consumed_keys = {
    "nlu",
    "accessibility",
    "route",
    "routes",
    "tourism_info",
    "venue info",
    "location_ner",
    "locationner",
  }

  extra_chunks: list[str] = []
  for key, value in tool_results.items():
    if key in consumed_keys:
      continue
    if not isinstance(value, str) or not value.strip():
      continue
    extra_chunks.append(f"- {key}:\n{value}")

  if not extra_chunks:
    return "{}"

  return "\n\n".join(extra_chunks)

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
      tool_results: Dict with tool payloads from pipeline execution.
        profile_context: Optional profile context with prompt_directives and ranking_bias.

    Returns:
        Complete prompt string for LLM invocation.
    """
    profile_section = _build_profile_section(profile_context) if profile_context else ""
    nlu = _tool_value(tool_results, "nlu")
    accessibility = _tool_value(tool_results, "accessibility")
    routes = _tool_value(tool_results, "routes", "route")
    tourism_info = _tool_value(tool_results, "venue info", "tourism_info")
    location_ner = _tool_value(tool_results, "locationner", "location_ner")
    additional_tools = _build_additional_tools_section(tool_results)

    return f"""Eres un asistente experto en turismo accesible en España.

El usuario preguntó: "{user_input}"

He analizado su consulta usando varias herramientas especializadas:

ANÁLISIS DE INTENCIÓN:
{nlu}

ANÁLISIS DE UBICACIÓN (NER):
{location_ner}

ANÁLISIS DE ACCESIBILIDAD:
{accessibility}

PLANIFICACIÓN DE RUTAS:
{routes}

INFORMACIÓN TURÍSTICA:
{tourism_info}

RESULTADOS ADICIONALES DE HERRAMIENTAS:
{additional_tools}
{profile_section}
Tu respuesta debe tener DOS partes:

PARTE 1 — Texto conversacional en español:
Genera una respuesta completa y útil que incluya:
1. Recomendaciones específicas de lugares accesibles
2. Información práctica sobre rutas y transporte
3. Horarios, precios y servicios de accesibilidad
4. Consejos específicos para las necesidades del usuario
Sé conversacional, útil y enfócate en los aspectos de accesibilidad.

Reglas de consistencia para la PARTE 1:
- Usa prioritariamente la INFORMACIÓN TURÍSTICA y las RUTAS proporcionadas por herramientas.
- No inventes venues concretos que no aparezcan en las salidas de herramientas.
- Si faltan datos en herramientas, dilo explícitamente y propone alternativas conservadoras.
- Si hay conflicto entre fuentes, prioriza datos estructurados de herramientas sobre suposiciones.

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
