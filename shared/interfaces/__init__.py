"""Interfaces y contratos entre capas"""

from shared.interfaces.accessibility_interface import AccessibilityServiceInterface
from shared.interfaces.directions_interface import DirectionsServiceInterface
from shared.interfaces.geocoding_interface import GeocodingServiceInterface
from shared.interfaces.interfaces import (
    AudioProcessorInterface,
    AuthInterface,
    BackendInterface,
    ConversationInterface,
    StorageInterface,
)
from shared.interfaces.ner_interface import NERServiceInterface
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.interfaces.places_interface import PlacesServiceInterface

__all__ = [
    "AccessibilityServiceInterface",
    "AudioProcessorInterface",
    "BackendInterface",
    "ConversationInterface",
    "AuthInterface",
    "DirectionsServiceInterface",
    "GeocodingServiceInterface",
    "NERServiceInterface",
    "NLUServiceInterface",
    "PlacesServiceInterface",
    "StorageInterface",
]
