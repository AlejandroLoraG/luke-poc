"""
Session Management API Router

Provides REST endpoints for creating and managing user sessions.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

from ..core.shared_managers import session_manager, chat_binding_manager
from ..core.config import settings

router = APIRouter(prefix="/api/v1", tags=["sessions"])
logger = logging.getLogger(__name__)


# Response Models
class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    user_identifier: str


class ChatBindingResponse(BaseModel):
    conversation_id: str
    session_id: str
    created_at: str
    bound_workflow_id: str | None = None
    is_bound: bool
    last_activity: str


class SessionDetailResponse(BaseModel):
    session: SessionResponse
    chats: List[ChatBindingResponse]
    total_chats: int


@router.post("/sessions", response_model=SessionResponse)
async def create_session(user_identifier: str = "anonymous") -> SessionResponse:
    """
    Create a new user session.

    Args:
        user_identifier: Optional identifier for the user (IP, browser fingerprint, manual ID)

    Returns:
        SessionResponse with session details
    """
    try:
        session = session_manager.create_session(user_identifier)

        return SessionResponse(
            session_id=session.session_id,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            user_identifier=session.user_identifier
        )

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str) -> SessionDetailResponse:
    """
    Get session details including all associated chats.

    Args:
        session_id: Unique session identifier

    Returns:
        SessionDetailResponse with session and chat information
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Get all chats for this session
        bindings = chat_binding_manager.get_session_bindings(session_id)

        chat_responses = [
            ChatBindingResponse(
                conversation_id=binding.conversation_id,
                session_id=binding.session_id,
                created_at=binding.created_at.isoformat(),
                bound_workflow_id=binding.bound_workflow_id,
                is_bound=binding.is_bound(),
                last_activity=binding.last_activity.isoformat()
            )
            for binding in bindings
        ]

        return SessionDetailResponse(
            session=SessionResponse(
                session_id=session.session_id,
                created_at=session.created_at.isoformat(),
                last_activity=session.last_activity.isoformat(),
                user_identifier=session.user_identifier
            ),
            chats=chat_responses,
            total_chats=len(chat_responses)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(limit: int = 50) -> List[SessionResponse]:
    """
    List all sessions, most recent first.

    Args:
        limit: Maximum number of sessions to return (default: 50)

    Returns:
        List of SessionResponse objects
    """
    try:
        sessions = session_manager.list_sessions(limit=limit)

        return [
            SessionResponse(
                session_id=session.session_id,
                created_at=session.created_at.isoformat(),
                last_activity=session.last_activity.isoformat(),
                user_identifier=session.user_identifier
            )
            for session in sessions
        ]

    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """
    Delete a session and all associated chat bindings.

    Args:
        session_id: Unique session identifier

    Returns:
        Success message
    """
    try:
        # Delete all chat bindings for this session
        bindings = chat_binding_manager.get_session_bindings(session_id)
        for binding in bindings:
            chat_binding_manager.delete_binding(binding.conversation_id)

        # Delete the session
        success = session_manager.delete_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return {"message": f"Session {session_id} and {len(bindings)} chat(s) deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/chats/{conversation_id}/binding", response_model=ChatBindingResponse)
async def get_chat_binding(conversation_id: str) -> ChatBindingResponse:
    """
    Get binding information for a specific chat.

    Args:
        conversation_id: Unique conversation identifier

    Returns:
        ChatBindingResponse with binding details
    """
    try:
        binding = chat_binding_manager.get_binding(conversation_id)

        if not binding:
            raise HTTPException(status_code=404, detail=f"Chat binding for {conversation_id} not found")

        return ChatBindingResponse(
            conversation_id=binding.conversation_id,
            session_id=binding.session_id,
            created_at=binding.created_at.isoformat(),
            bound_workflow_id=binding.bound_workflow_id,
            is_bound=binding.is_bound(),
            last_activity=binding.last_activity.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat binding {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat binding: {str(e)}")


@router.get("/sessions/stats")
async def get_session_stats() -> Dict[str, Any]:
    """
    Get statistics about sessions and chat bindings.

    Returns:
        Dictionary with session and binding metrics
    """
    try:
        session_stats = session_manager.get_stats()
        binding_stats = chat_binding_manager.get_stats()

        return {
            "sessions": session_stats,
            "chat_bindings": binding_stats
        }

    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
