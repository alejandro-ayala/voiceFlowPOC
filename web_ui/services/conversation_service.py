"""
Conversation service implementing ConversationInterface.
Handles chat sessions and conversation history (in-memory for PoC).
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import structlog

from ..core.interfaces import ConversationInterface
from ..config.settings import Settings

logger = structlog.get_logger(__name__)


class ConversationService(ConversationInterface):
    """
    In-memory conversation service for PoC.
    Can be easily extended to use database storage.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def add_message(self, user_message: str, ai_response: str, session_id: Optional[str] = None) -> str:
        """Add message pair to conversation"""
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Initialize session if new
            if session_id not in self.conversations:
                await self._initialize_session(session_id)
            
            # Create message pair
            message_pair = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "user_message": user_message,
                "ai_response": ai_response,
                "message_type": "conversation_pair"
            }
            
            # Add to conversation
            self.conversations[session_id].append(message_pair)
            
            # Update session metadata
            self.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
            self.session_metadata[session_id]["message_count"] += 1
            
            logger.info("💬 Message pair added to conversation", 
                       session_id=session_id, 
                       total_messages=len(self.conversations[session_id]))
            
            return session_id
            
        except Exception as e:
            logger.error("❌ Failed to add message to conversation", error=str(e))
            raise
    
    async def _initialize_session(self, session_id: str) -> None:
        """Initialize a new conversation session"""
        self.conversations[session_id] = []
        self.session_metadata[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0,
            "session_type": "demo"
        }
        
        logger.info("🆕 New conversation session initialized", session_id=session_id)
    
    async def get_conversation_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conversation history for session"""
        try:
            if not session_id:
                # Return all conversations if no session specified
                all_conversations = []
                for sid, messages in self.conversations.items():
                    for message in messages:
                        message_copy = message.copy()
                        message_copy["session_id"] = sid
                        all_conversations.append(message_copy)
                return sorted(all_conversations, key=lambda x: x["timestamp"])
            
            # Return specific session
            if session_id in self.conversations:
                logger.info("📜 Retrieved conversation history", 
                           session_id=session_id, 
                           message_count=len(self.conversations[session_id]))
                return self.conversations[session_id].copy()
            else:
                logger.warning("⚠️ Session not found", session_id=session_id)
                return []
                
        except Exception as e:
            logger.error("❌ Failed to get conversation history", error=str(e))
            return []
    
    async def clear_conversation(self, session_id: Optional[str] = None) -> bool:
        """Clear conversation history"""
        try:
            if session_id:
                # Clear specific session
                if session_id in self.conversations:
                    del self.conversations[session_id]
                    del self.session_metadata[session_id]
                    logger.info("🧹 Conversation cleared", session_id=session_id)
                    return True
                else:
                    logger.warning("⚠️ Session not found for clearing", session_id=session_id)
                    return False
            else:
                # Clear all conversations
                cleared_count = len(self.conversations)
                self.conversations.clear()
                self.session_metadata.clear()
                logger.info("🧹 All conversations cleared", count=cleared_count)
                return True
                
        except Exception as e:
            logger.error("❌ Failed to clear conversation", error=str(e))
            return False
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        try:
            if session_id in self.session_metadata:
                session_info = self.session_metadata[session_id].copy()
                session_info["current_message_count"] = len(self.conversations.get(session_id, []))
                return session_info
            return None
        except Exception as e:
            logger.error("❌ Failed to get session info", error=str(e))
            return None
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all session metadata"""
        try:
            sessions = []
            for session_id, metadata in self.session_metadata.items():
                session_info = metadata.copy()
                session_info["current_message_count"] = len(self.conversations.get(session_id, []))
                sessions.append(session_info)
            
            # Sort by last activity (most recent first)
            sessions.sort(key=lambda x: x["last_activity"], reverse=True)
            return sessions
        except Exception as e:
            logger.error("❌ Failed to get all sessions", error=str(e))
            return []
    
    async def export_conversation(self, session_id: str, format: str = "json") -> Optional[Dict[str, Any]]:
        """Export conversation in specified format"""
        try:
            if session_id not in self.conversations:
                return None
            
            conversation = self.conversations[session_id]
            metadata = self.session_metadata[session_id]
            
            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "format": format,
                    "version": "1.0"
                },
                "session_metadata": metadata,
                "conversation": conversation,
                "statistics": {
                    "total_messages": len(conversation),
                    "session_duration": self._calculate_session_duration(conversation),
                    "average_response_time": "N/A"  # Could be calculated if we track timing
                }
            }
            
            logger.info("📤 Conversation exported", session_id=session_id, format=format)
            return export_data
            
        except Exception as e:
            logger.error("❌ Failed to export conversation", error=str(e))
            return None
    
    def _calculate_session_duration(self, conversation: List[Dict[str, Any]]) -> str:
        """Calculate session duration from first to last message"""
        if len(conversation) < 2:
            return "0 minutes"
        
        try:
            first_time = datetime.fromisoformat(conversation[0]["timestamp"])
            last_time = datetime.fromisoformat(conversation[-1]["timestamp"])
            duration = last_time - first_time
            
            minutes = int(duration.total_seconds() / 60)
            seconds = int(duration.total_seconds() % 60)
            
            if minutes > 0:
                return f"{minutes} minutes, {seconds} seconds"
            else:
                return f"{seconds} seconds"
        except:
            return "Unknown"
