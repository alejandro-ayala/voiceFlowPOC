"""NLU keyword patterns for intent, destination, and accessibility extraction."""

INTENT_PATTERNS: dict[str, list[str]] = {
    "route_planning": ["ruta", "llegar", "cómo", "como", "ir", "transporte"],
    "event_search": ["concierto", "evento", "actividad", "plan", "ocio"],
    "restaurant_search": ["restaurante", "comer", "comida"],
    "accommodation_search": ["hotel", "alojamiento", "dormir"],
}

DESTINATION_PATTERNS: dict[str, list[str]] = {
    "Museo del Prado": ["prado", "museo del prado"],
    "Museo Reina Sofía": ["reina sofía", "reina sofia"],
    "Museo Thyssen": ["thyssen"],
    "Parque del Retiro": ["retiro"],
    "Palacio Real": ["palacio real"],
    "Templo de Debod": ["templo debod"],
    "Espacios musicales Madrid": ["concierto", "música", "musica"],
    "Restaurantes Madrid": ["restaurante"],
    "Parques Madrid": ["parque"],
    "Teatros Madrid": ["teatro"],
}

# Special pattern: "madrid" without any specific venue
MADRID_GENERAL_KEYWORDS: list[str] = ["madrid"]
MADRID_SPECIFIC_EXCLUSIONS: list[str] = ["prado", "reina", "thyssen"]

ACCESSIBILITY_PATTERNS: dict[str, list[str]] = {
    "wheelchair": ["silla de ruedas", "wheelchair", "accesible", "movilidad"],
    "visual_impairment": ["visual", "ciego", "braille"],
    "hearing_impairment": ["auditivo", "sordo", "señas"],
}
