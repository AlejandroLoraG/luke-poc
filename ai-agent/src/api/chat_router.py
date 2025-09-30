import uuid
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, AsyncGenerator

from shared.schemas import ChatRequest, ChatResponse
from ..core.config import settings
from ..core.conversation_manager import ConversationManager
from ..core.workflow_storage import workflow_storage
from ..core.streaming_service import streaming_service
from ..agents.workflow_conversation_agent import WorkflowConversationAgent

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Configure logging
logger = logging.getLogger(__name__)

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


async def generate_sse_stream(
    message: str,
    conversation_id: str,
    workflow_spec_dict: Optional[Dict[str, Any]] = None,
    workflow_source: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events stream for chat responses using the streaming service.

    This function serves as a bridge between the FastAPI endpoint and the
    dedicated streaming service, handling conversation management integration.
    """
    try:
        # Get conversation history and agent
        history = conversation_manager.get_context_string(conversation_id)
        agent = await get_workflow_agent()

        # Collect response data for conversation storage
        response_chunks = []
        all_tools_used = []

        # Generate SSE stream using the dedicated streaming service
        async for sse_event in streaming_service.generate_sse_stream(
            agent=agent,
            message=message,
            conversation_id=conversation_id,
            workflow_spec=workflow_spec_dict,
            workflow_source=workflow_source,
            conversation_history=history,
            user_context={}
        ):
            # Track response data for conversation management
            if '"type": "chunk"' in sse_event:
                # Extract chunk data for conversation storage
                try:
                    chunk_data = json.loads(sse_event.split('data: ')[1].split('\n')[0])
                    if chunk_data.get('type') == 'chunk':
                        response_chunks.append(chunk_data.get('content', ''))
                except (json.JSONDecodeError, IndexError):
                    pass  # Continue streaming even if parsing fails

            elif '"type": "complete"' in sse_event:
                # Add conversation management data to completion event
                try:
                    event_data = json.loads(sse_event.split('data: ')[1].split('\n')[0])

                    # Store conversation turn
                    complete_response = "".join(response_chunks)
                    prompt_count = conversation_manager.add_turn(
                        conversation_id=conversation_id,
                        user_message=message,
                        agent_response=complete_response,
                        mcp_tools_used=event_data.get('mcp_tools_used', [])
                    )

                    # Add prompt count to completion event
                    event_data['prompt_count'] = prompt_count
                    yield f"data: {json.dumps(event_data)}\n\n"
                    continue

                except (json.JSONDecodeError, IndexError):
                    pass  # Fallback to original event

            yield sse_event

    except Exception as e:
        # Send error event
        error_data = {
            "type": "error",
            "error": str(e),
            "conversation_id": conversation_id
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/chat/stream")
async def stream_chat_with_agent(request: ChatRequest) -> StreamingResponse:
    """
    Stream chat responses with the workflow agent using Server-Sent Events.
    """
    try:
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())

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

        # Create the streaming generator
        stream_generator = generate_sse_stream(
            message=request.message,
            conversation_id=conversation_id,
            workflow_spec_dict=workflow_spec_dict,
            workflow_source=workflow_source
        )

        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming error: {str(e)}")