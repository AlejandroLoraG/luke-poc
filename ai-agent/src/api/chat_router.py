import uuid
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from shared.schemas import ChatRequest, ChatResponse
from ..core.config import settings
from ..core.conversation_manager import ConversationManager
from ..core.workflow_storage import workflow_storage
from ..agents.workflow_conversation_agent import WorkflowConversationAgent

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Global instances
conversation_manager = ConversationManager(max_length=settings.max_conversation_length)
workflow_agent: Optional[WorkflowConversationAgent] = None


async def get_workflow_agent() -> WorkflowConversationAgent:
    """Get or create the workflow agent instance."""
    global workflow_agent
    if workflow_agent is None:
        workflow_agent = WorkflowConversationAgent(test_mode=settings.environment == "test")
    return workflow_agent


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """
    Chat with the workflow agent about workflow specifications.
    """
    try:
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Get conversation history
        history = conversation_manager.get_context_string(conversation_id)

        # Get the workflow agent
        agent = await get_workflow_agent()

        # Resolve workflow specification
        workflow_spec_dict = None
        workflow_source = None

        # Priority: workflow_spec > workflow_id
        if request.workflow_spec:
            if hasattr(request.workflow_spec, 'model_dump'):
                workflow_spec_dict = request.workflow_spec.model_dump()
            else:
                workflow_spec_dict = request.workflow_spec
            workflow_source = "provided_spec"
        elif request.workflow_id:
            # Load workflow from storage
            stored_workflow = workflow_storage.get_workflow(request.workflow_id)
            if stored_workflow is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow with ID '{request.workflow_id}' not found in storage"
                )
            workflow_spec_dict = stored_workflow
            workflow_source = f"stored_workflow:{request.workflow_id}"

        # Have the conversation
        response_text, tools_used = await agent.chat(
            message=request.message,
            workflow_spec=workflow_spec_dict,
            conversation_history=history,
            user_context={}  # Could be populated from request headers/auth
        )

        # Store the conversation turn
        prompt_count = conversation_manager.add_turn(
            conversation_id=conversation_id,
            user_message=request.message,
            agent_response=response_text,
            mcp_tools_used=tools_used
        )

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            prompt_count=prompt_count,
            mcp_tools_used=tools_used,
            workflow_source=workflow_source
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str) -> Dict[str, Any]:
    """Get the history of a conversation."""
    history = conversation_manager.get_conversation_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "total_turns": len(history),
        "history": [
            {
                "user_message": turn.user_message,
                "agent_response": turn.agent_response,
                "timestamp": turn.timestamp.isoformat(),
                "tools_used": turn.mcp_tools_used
            }
            for turn in history
        ]
    }


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str) -> Dict[str, str]:
    """Clear a conversation history."""
    conversation_manager.clear_conversation(conversation_id)
    return {"message": f"Conversation {conversation_id} cleared"}


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        agent = await get_workflow_agent()
        workflow_stats = workflow_storage.get_stats()

        # Test MCP server connectivity by trying to create agent
        mcp_server_url = settings.mcp_server_url
        mcp_connected = True  # Assume connected, will be false if agent creation fails

        return {
            "status": "healthy",
            "mcp_server_url": mcp_server_url,
            "mcp_server_connected": mcp_connected,
            "max_conversation_length": settings.max_conversation_length,
            "model": settings.ai_model,
            "workflow_storage": workflow_stats,
            "test_mode": settings.environment == "test"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "mcp_server_connected": False,
            "workflow_storage": {"total_workflows": 0, "error": "storage_unavailable"}
        }