"""
Core interfaces following SOLID principles.
These abstractions allow for easy testing, mocking, and future implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class AudioProcessorInterface(ABC):
    """
    Interface for audio processing operations.
    Follows ISP by being specific to audio functionality.
    """
    
    @abstractmethod
    async def validate_audio(self, audio_data: bytes, filename: str) -> bool:
        """Validate audio file format and size"""
        pass
    
    @abstractmethod
    async def process_audio_file(self, audio_path: Path) -> str:
        """Process audio file and return transcription"""
        pass
    
    @abstractmethod
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        pass


class BackendInterface(ABC):
    """
    Interface for backend communication.
    Allows switching between local backend and future cloud implementations.
    """
    
    @abstractmethod
    async def process_query(self, transcription: str) -> Dict[str, Any]:
        """Process user query through multi-agent system"""
        pass
    
    @abstractmethod
    async def get_system_status(self) -> Dict[str, Any]:
        """Get backend system health status"""
        pass
    
    @abstractmethod
    async def clear_conversation(self) -> bool:
        """Clear conversation history"""
        pass


class ConversationInterface(ABC):
    """
    Interface for conversation management.
    Handles chat history and session management.
    """
    
    @abstractmethod
    async def add_message(self, user_message: str, ai_response: str) -> str:
        """Add message pair to conversation"""
        pass
    
    @abstractmethod
    async def get_conversation_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conversation history"""
        pass
    
    @abstractmethod
    async def clear_conversation(self, session_id: Optional[str] = None) -> bool:
        """Clear conversation history"""
        pass


class AuthInterface(ABC):
    """
    Interface for authentication (future implementation).
    Ready for easy integration when needed.
    """
    
    @abstractmethod
    async def authenticate_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with token"""
        pass
    
    @abstractmethod
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions"""
        pass


class StorageInterface(ABC):
    """
    Interface for data persistence (future implementation).
    Allows easy switching between local storage, database, or cloud storage.
    """
    
    @abstractmethod
    async def save_conversation(self, session_id: str, conversation: List[Dict[str, Any]]) -> bool:
        """Save conversation to storage"""
        pass
    
    @abstractmethod
    async def load_conversation(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Load conversation from storage"""
        pass
    
    @abstractmethod
    async def delete_conversation(self, session_id: str) -> bool:
        """Delete conversation from storage"""
        pass
