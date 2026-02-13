"""Interfaces y contratos entre capas"""

from shared.interfaces.interfaces import (
    AudioProcessorInterface,
    AuthInterface,
    BackendInterface,
    ConversationInterface,
    StorageInterface,
)

__all__ = [
    "AudioProcessorInterface",
    "BackendInterface",
    "ConversationInterface",
    "AuthInterface",
    "StorageInterface",
]
