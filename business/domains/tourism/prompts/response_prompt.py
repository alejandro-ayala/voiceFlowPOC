"""Response prompt builder for the tourism domain."""


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

Genera una respuesta completa y útil en español que incluya:
1. Recomendaciones específicas de lugares accesibles
2. Información práctica sobre rutas y transporte
3. Horarios, precios y servicios de accesibilidad
4. Consejos específicos para las necesidades del usuario

Sé conversacional, útil y enfócate en los aspectos de accesibilidad."""
