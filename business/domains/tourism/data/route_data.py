"""Route database for accessible transport in Madrid."""

ROUTE_DB: dict[str, dict] = {
    "Museo del Prado": {
        "routes": [
            {
                "id": "route_1",
                "transport": "metro",
                "duration": "25 min",
                "accessibility": "full",
                "steps": [
                    "Walk to Sol Metro Station (3 min)",
                    "Take Line 2 to Banco de España (15 min)",
                    "Walk to Museo del Prado (7 min)",
                ],
                "accessibility_features": [
                    "elevator_access",
                    "tactile_guidance",
                    "audio_announcements",
                ],
            },
            {
                "id": "route_2",
                "transport": "bus",
                "duration": "35 min",
                "accessibility": "full",
                "steps": [
                    "Walk to Gran Vía bus stop (5 min)",
                    "Take Bus 27 to Cibeles (20 min)",
                    "Walk to Museo del Prado (10 min)",
                ],
                "accessibility_features": [
                    "low_floor_bus",
                    "wheelchair_space",
                    "audio_stops",
                ],
            },
        ],
        "cost": "2.50€ (metro) / 1.50€ (bus)",
    },
    "Museo Reina Sofía": {
        "routes": [
            {
                "id": "route_1",
                "transport": "metro",
                "duration": "20 min",
                "accessibility": "full",
                "steps": [
                    "Walk to Sol Metro Station (3 min)",
                    "Take Line 1 to Atocha (12 min)",
                    "Walk to Reina Sofía (5 min)",
                ],
                "accessibility_features": [
                    "elevator_access",
                    "tactile_guidance",
                    "audio_announcements",
                ],
            }
        ],
        "cost": "2.50€ (metro)",
    },
    "Espacios musicales": {
        "routes": [
            {
                "id": "route_1",
                "transport": "metro",
                "duration": "varies",
                "accessibility": "partial",
                "steps": [
                    "Check specific venue location",
                    "Most concert halls accessible via Metro Lines 1-10",
                    "Venues typically near metro stations",
                ],
                "accessibility_features": [
                    "elevator_access",
                    "wheelchair_spaces_reserved",
                ],
            }
        ],
        "cost": "2.50€ + venue ticket",
    },
}

DEFAULT_ROUTE: dict = {
    "routes": [
        {
            "id": "route_1",
            "transport": "metro",
            "duration": "varies",
            "accessibility": "check_specific",
            "steps": [
                "Identify specific destination",
                "Use Metro Lines 1-12",
                "Most stations have elevator access",
            ],
            "accessibility_features": [
                "elevator_access",
                "tactile_guidance",
            ],
        }
    ],
    "cost": "2.50€ (metro) / 1.50€ (bus)",
}
