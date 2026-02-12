"""Accessibility database for Madrid tourism venues."""

ACCESSIBILITY_DB: dict[str, dict] = {
    "Museo del Prado": {
        "accessibility_level": "full_wheelchair_access",
        "venue_rating": 4.8,
        "facilities": [
            "wheelchair_ramps",
            "adapted_bathrooms",
            "audio_guides",
            "tactile_paths",
            "sign_language_interpreters",
        ],
        "accessibility_score": 9.2,
        "certification": "ONCE_certified",
    },
    "Museo Reina Sofía": {
        "accessibility_level": "full_wheelchair_access",
        "venue_rating": 4.6,
        "facilities": [
            "wheelchair_ramps",
            "adapted_bathrooms",
            "audio_guides",
            "elevator_access",
        ],
        "accessibility_score": 8.8,
        "certification": "ONCE_certified",
    },
    "Espacios musicales Madrid": {
        "accessibility_level": "partial_wheelchair_access",
        "venue_rating": 4.2,
        "facilities": [
            "wheelchair_spaces",
            "hearing_loops",
            "sign_language_interpreters",
        ],
        "accessibility_score": 7.5,
        "certification": "municipal_certified",
    },
    "Restaurantes Madrid": {
        "accessibility_level": "varies_by_location",
        "venue_rating": 3.8,
        "facilities": ["some_wheelchair_access", "varied_bathroom_access"],
        "accessibility_score": 6.5,
        "certification": "mixed",
    },
}

DEFAULT_ACCESSIBILITY: dict = {
    "accessibility_level": "partial_access",
    "venue_rating": 3.5,
    "facilities": ["basic_access"],
    "accessibility_score": 6.0,
    "certification": "not_certified",
}
