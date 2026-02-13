"""
Chat API endpoints for the VoiceFlow PoC.

Handles conversation management and AI responses.
Backend responses are simulated for demo purposes to avoid OpenAI costs.
"""

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException

from application.models.requests import ChatMessageRequest
from application.models.responses import (
    ChatResponse,
    ConversationListResponse,
    ConversationResponse,
)
from shared.exceptions.exceptions import (
    BackendCommunicationException,
    ValidationException,
)
from shared.interfaces.interfaces import BackendInterface, ConversationInterface
from shared.utils.dependencies import get_backend_adapter, get_conversation_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatMessageRequest,
    backend_service: BackendInterface = Depends(get_backend_adapter),
    conversation_service: ConversationInterface = Depends(get_conversation_service),
):
    """
    Send a message to the AI backend and get a response.

    This endpoint processes real AI responses from LangChain agents.
    The conversation history is properly managed and persisted.
    """
    try:
        # Validate input
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Create or get conversation
        conversation_id = request.conversation_id or str(uuid.uuid4())

        logger.info(
            "🗨️ Processing chat message",
            conversation_id=conversation_id,
            message_length=len(request.message),
        )

        # Get AI response from backend (real agents)
        backend_response = await backend_service.process_query(transcription=request.message.strip())

        # Add message pair to conversation service (for session management)
        session_id = await conversation_service.add_message(
            user_message=request.message.strip(),
            ai_response=backend_response["ai_response"],
            session_id=conversation_id,
        )

        return ChatResponse(
            status="success",
            message="Message processed successfully",
            session_id=session_id,
            ai_response=backend_response["ai_response"],
            processing_time=backend_response.get("processing_time", 0.5),
            intent=backend_response.get("intent"),
            entities=backend_response.get("entities"),
            tourism_data=backend_response.get("tourism_data"),
        )

    except BackendCommunicationException as e:
        # Log error for debugging (no conversation update needed)
        logger.error("Backend communication error", error=str(e))
        raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")

    except ValidationException as e:
        logger.error("Validation error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)}")

    except Exception as e:
        logger.error("Unexpected error in chat endpoint", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    conversation_service: ConversationInterface = Depends(get_conversation_service),
):
    """
    Get conversation history by ID.
    """
    try:
        conversation = await conversation_service.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return ConversationResponse(
            success=True,
            conversation_id=conversation_id,
            messages=conversation["messages"],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
            message_count=len(conversation["messages"]),
            message="Conversation retrieved successfully",
        )

    except ValidationException as e:
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 10,
    offset: int = 0,
    conversation_service: ConversationInterface = Depends(get_conversation_service),
):
    """
    List all conversations with pagination.
    """
    try:
        conversations = await conversation_service.list_conversations(limit=limit, offset=offset)

        return ConversationListResponse(
            success=True,
            conversations=conversations,
            total_count=len(conversations),
            limit=limit,
            offset=offset,
            message="Conversations retrieved successfully",
        )

    except ValidationException as e:
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    conversation_service: ConversationInterface = Depends(get_conversation_service),
):
    """
    Delete a conversation by ID.
    """
    try:
        success = await conversation_service.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "Conversation deleted successfully",
        }

    except ValidationException as e:
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/conversation/{conversation_id}/clear")
async def clear_conversation(
    conversation_id: str,
    conversation_service: ConversationInterface = Depends(get_conversation_service),
):
    """
    Clear all messages from a conversation but keep the conversation.
    """
    try:
        success = await conversation_service.clear_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "Conversation cleared successfully",
        }

    except ValidationException as e:
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/analyze-transcription", response_model=ChatResponse)
async def analyze_transcription(
    transcription: str,
    conversation_id: Optional[str] = None,
    context: Optional[dict] = None,
    backend_service: BackendInterface = Depends(get_backend_adapter),
    conversation_service: ConversationInterface = Depends(get_conversation_service),
):
    """
    Analyze transcribed audio text and get AI response.
    This is a convenience endpoint that combines transcription results with chat.
    """
    try:
        # Validate transcription
        if not transcription or not transcription.strip():
            raise HTTPException(status_code=400, detail="Transcription cannot be empty")

        # Create request object
        chat_request = ChatMessageRequest(
            message=transcription.strip(),
            conversation_id=conversation_id,
            context=context or {"source": "audio_transcription"},
            timestamp=None,  # Will be set automatically
        )

        # Reuse the send_message logic
        return await send_message(
            request=chat_request,
            backend_service=backend_service,
            conversation_service=conversation_service,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/demo/responses")
async def get_demo_responses():
    """
    Get sample demo responses for testing the UI.
    This endpoint shows what kind of responses the system can generate.
    """
    return {
        "success": True,
        "sample_responses": [
            {
                "input": "¿Qué lugares puedo visitar en Madrid?",
                "response": (
                    "Madrid ofrece increíbles opciones turísticas. Te recomiendo visitar el Museo del Prado,"
                    " el Palacio Real, el Parque del Retiro y la Plaza Mayor. Para una experiencia más local,"
                    " explora el barrio de Malasaña y prueba tapas en el Mercado de San Miguel."
                ),
                "confidence": 0.95,
            },
            {
                "input": "¿Cuál es el mejor momento para viajar a Barcelona?",
                "response": (
                    "El mejor momento para visitar Barcelona es durante la primavera (abril-junio) y el otoño"
                    " (septiembre-octubre). El clima es agradable, hay menos turistas que en verano, y los precios"
                    " suelen ser más razonables. Evita agosto si prefieres menos multitudes."
                ),
                "confidence": 0.92,
            },
            {
                "input": "¿Qué documentos necesito para viajar a España?",
                "response": (
                    "Para viajar a España necesitas: pasaporte válido (ciudadanos no-UE) o DNI (ciudadanos UE),"
                    " posible visa según tu nacionalidad, seguro de viaje recomendado, y prueba de fondos"
                    " suficientes si te lo solicitan en el control fronterizo."
                ),
                "confidence": 0.98,
            },
        ],
        "message": "Demo responses available for testing",
    }
