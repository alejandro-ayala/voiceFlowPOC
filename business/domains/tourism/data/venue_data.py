"""Venue information database for Madrid tourism."""

VENUE_DB: dict[str, dict] = {
    "Museo del Prado": {
        "opening_hours": {
            "monday_saturday": "10:00-20:00",
            "sunday_holidays": "10:00-19:00",
            "special_hours": "Extended until 22:00 on Saturdays",
        },
        "pricing": {
            "general": "15€",
            "reduced": "7.50€ (students, seniors 65+)",
            "free": "EU citizens under 18, disabled visitors + companion",
        },
        "accessibility_reviews": [
            "Excellent wheelchair access throughout",
            "Audio guides in multiple languages",
            "Staff trained in accessibility needs",
            "Tactile reproductions available",
        ],
        "special_exhibitions": [
            "Velázquez retrospective (until March 2026)",
            "Goya prints collection",
        ],
        "accessibility_services": {
            "wheelchair_rental": "Available at entrance",
            "sign_language_tours": "Saturdays 11:00",
            "tactile_tours": "By appointment",
            "accessible_parking": "Calle Felipe IV",
        },
        "contact": {
            "accessibility_coordinator": "+34 91 330 2800",
            "advance_booking": "accesibilidad@museodelprado.es",
        },
    },
    "Museo Reina Sofía": {
        "opening_hours": {
            "monday_saturday": "10:00-21:00",
            "sunday": "10:00-19:00",
            "tuesday_closed": "Closed on Tuesdays",
        },
        "pricing": {
            "general": "12€",
            "reduced": "6€ (students, seniors 65+)",
            "free": "Under 18, disabled visitors + companion",
        },
        "accessibility_reviews": [
            "Full wheelchair accessibility",
            "Modern elevator systems",
            "Audio guides available",
            "Accessible exhibition spaces",
        ],
        "special_exhibitions": [
            "Picasso contemporary works",
            "Spanish avant-garde collection",
        ],
        "accessibility_services": {
            "wheelchair_rental": "Free at entrance",
            "audio_guides": "Available",
            "accessible_parking": "Calle Santa Isabel",
        },
        "contact": {
            "accessibility_coordinator": "+34 91 774 1000",
            "advance_booking": "accesibilidad@museoreinasofia.es",
        },
    },
    "Espacios musicales Madrid": {
        "opening_hours": {
            "varies": "Depends on venue and event",
            "general": "Evening concerts 19:00-23:00",
        },
        "pricing": {
            "varies": "15€-80€ depending on venue and performance",
            "reduced": "Student and disability discounts available",
        },
        "accessibility_reviews": [
            "Most major venues wheelchair accessible",
            "Reserved wheelchair spaces",
            "Hearing loops available",
            "Sign language interpretation on request",
        ],
        "special_exhibitions": [
            "Teatro Real opera season",
            "Auditorio Nacional concerts",
            "Jazz clubs with accessibility",
        ],
        "accessibility_services": {
            "wheelchair_spaces": "Reserved seating",
            "hearing_assistance": "Available",
            "accessible_parking": "Varies by venue",
        },
        "contact": {
            "accessibility_coordinator": "Contact specific venue",
            "advance_booking": "Required for accessibility services",
        },
    },
    "Restaurantes accesibles Madrid": {
        "opening_hours": {
            "lunch": "13:00-16:00",
            "dinner": "20:00-24:00",
            "varies": "Depends on establishment",
        },
        "pricing": {
            "varies": "15€-60€ per person",
            "accessibility": "No additional charges for accessibility",
        },
        "accessibility_reviews": [
            "Many restaurants now wheelchair accessible",
            "Braille menus available in some locations",
            "Staff training improving",
            "Accessible bathrooms increasingly common",
        ],
        "special_exhibitions": [
            "Traditional Spanish cuisine",
            "Modern fusion restaurants",
            "Accessible tapas bars",
        ],
        "accessibility_services": {
            "wheelchair_access": "Check in advance",
            "braille_menus": "Some locations",
            "accessible_parking": "Limited, use public transport",
        },
        "contact": {
            "accessibility_coordinator": "Contact restaurant directly",
            "advance_booking": "Recommended to confirm accessibility",
        },
    },
}

DEFAULT_VENUE: dict = {
    "opening_hours": {"general": "Varies by location and type"},
    "pricing": {
        "general": "Varies",
        "accessibility": "Discounts often available",
    },
    "accessibility_reviews": [
        "Accessibility varies by location",
        "Always call ahead to confirm",
    ],
    "special_exhibitions": ["Check specific venue websites"],
    "accessibility_services": {"varies": "Contact venue directly"},
    "contact": {"general": "Contact specific venue for accessibility information"},
}
