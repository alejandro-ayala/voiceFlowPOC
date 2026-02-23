"""Interfaces y contratos entre capas"""

from shared.interfaces.interfaces import (
    AudioProcessorInterface,
    AuthInterface,
    BackendInterface,
    ConversationInterface,
    StorageInterface,
)
from shared.interfaces.ner_interface import NERServiceInterface
from shared.interfaces.nlu_interface import NLUServiceInterface

__all__ = [
    "AudioProcessorInterface",
    "BackendInterface",
    "ConversationInterface",
    "AuthInterface",
    "StorageInterface",
    "NERServiceInterface",
    "NLUServiceInterface",
]
