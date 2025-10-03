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
from ..core.shared_managers import session_manager, chat_binding_manager
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

    Now includes session management and chat-to-workflow binding.
    """
    try:
        # 1. Validate session exists
        if not request.session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {request.session_id} not found. Please create a session first."
            )

        # Update session activity
        session_manager.update_activity(request.session_id)

        # 2. Get or create conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # 3. Get or create chat binding
        binding = chat_binding_manager.get_binding(conversation_id)

        if not binding:
            # Create new binding for this chat
            binding = chat_binding_manager.create_binding(conversation_id, request.session_id)
            logger.info(f"Created new chat binding: {conversation_id} in session: {request.session_id}")
        else:
            # Update binding activity
            chat_binding_manager.update_activity(conversation_id)

        # 4. Resolve workflow specification
        workflow_spec_dict = None
        workflow_source = None

        if binding.is_bound():
            # Chat is bound to a workflow - ALWAYS use that workflow
            workflow_id = binding.bound_workflow_id
            workflow_spec_dict = workflow_storage.get_workflow(workflow_id)

            if not workflow_spec_dict:
                logger.error(f"Bound workflow {workflow_id} not found in storage!")
                raise HTTPException(
                    status_code=500,
                    detail=f"Bound workflow {workflow_id} not found. Contact support."
                )

            workflow_source = f"bound_workflow:{workflow_id}"
            logger.info(f"🔒 Chat {conversation_id} is bound to workflow {workflow_id}")

        elif request.workflow_spec:
            # Not bound, but spec provided in request
            if hasattr(request.workflow_spec, 'model_dump'):
                workflow_spec_dict = request.workflow_spec.model_dump()
            else:
                workflow_spec_dict = request.workflow_spec
            workflow_source = "provided_spec"

        elif request.workflow_id:
            # Not bound, but workflow_id provided in request
            workflow_spec_dict = conversation_manager.get_workflow_cached(request.workflow_id)

            if workflow_spec_dict:
                workflow_source = f"cached_workflow:{request.workflow_id}"
            else:
                stored_workflow = workflow_storage.get_workflow(request.workflow_id)
                if stored_workflow is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Workflow with ID '{request.workflow_id}' not found in storage"
                    )
                workflow_spec_dict = stored_workflow
                conversation_manager.cache_workflow(request.workflow_id, workflow_spec_dict)
                workflow_source = f"stored_workflow:{request.workflow_id}"

        # 5. Get conversation history and metadata
        history = conversation_manager.get_context_string(conversation_id)
        turn_count = conversation_manager.get_conversation_count(conversation_id)

        # Get recent workflows for context
        workflow_memory = conversation_manager.get_workflow_memory(conversation_id)
        recent_workflows_refs = [
            {"spec_id": ref.spec_id, "name": ref.name, "action": ref.action}
            for ref in workflow_memory.get_recent_workflows(limit=5)
        ]

        # 6. Get the workflow agent
        agent = await get_workflow_agent()

        # 7. Prepare enhanced user context with session and binding info
        user_context = {
            "conversation_id": conversation_id,
            "session_id": request.session_id,
            "turn_count": turn_count,
            "conversation_workflows": recent_workflows_refs,
            "language": request.language.value,
            # NEW: Binding context for WorkflowContext
            "bound_workflow_id": binding.bound_workflow_id,
            "is_workflow_bound": binding.is_bound()
        }

        # 8. Have the conversation
        response_text, tools_used, workflow_created_id = await agent.chat(
            message=request.message,
            workflow_spec=workflow_spec_dict,
            conversation_history=history,
            user_context=user_context
        )

        # 9. Bind workflow if newly created and fetch it from svc-builder
        if workflow_created_id and not binding.is_bound():
            try:
                # Fetch the workflow from svc-builder and store it locally
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.svc_builder_url}/api/v1/workflows/{workflow_created_id}"
                    )
                    if response.status_code == 200:
                        workflow_data = response.json()
                        if "workflow_spec" in workflow_data:
                            workflow_storage.store_workflow(workflow_created_id, workflow_data["workflow_spec"])
                            logger.info(f"✅ Stored workflow {workflow_created_id} in ai-agent cache")

                binding = chat_binding_manager.bind_workflow(conversation_id, workflow_created_id)
                logger.info(f"✅ Bound chat {conversation_id} to newly created workflow {workflow_created_id}")
            except ValueError as e:
                logger.error(f"Failed to bind workflow: {e}")
                # Don't fail the request, but log the error
            except Exception as e:
                logger.error(f"Failed to fetch/store workflow: {e}")
                # Don't fail the request, but log the error

        # 10. Track workflow in conversation memory
        if workflow_spec_dict and "specId" in workflow_spec_dict:
            action = "created" if workflow_created_id == workflow_spec_dict["specId"] else "discussed"
            conversation_manager.track_workflow(
                conversation_id,
                spec_id=workflow_spec_dict["specId"],
                name=workflow_spec_dict.get("name", "Unnamed Workflow"),
                action=action
            )

        # 11. Store the conversation turn with workflow context
        prompt_count = conversation_manager.add_turn(
            conversation_id=conversation_id,
            user_message=request.message,
            agent_response=response_text,
            mcp_tools_used=tools_used
        )

        # 12. Return enhanced response with session and binding info
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            session_id=request.session_id,
            prompt_count=prompt_count,
            mcp_tools_used=tools_used,
            mcp_tools_requested=tools_used,
            workflow_created_id=workflow_created_id,
            workflow_bound_id=binding.bound_workflow_id,
            is_chat_locked=binding.is_bound(),
            workflow_source=workflow_source,
            language=request.language.value
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

        # Get cache statistics
        cache_stats = conversation_manager.get_cache_stats()

        return {
            "status": "healthy",
            "mcp_server_url": mcp_server_url,
            "mcp_server_connected": mcp_connected,
            "max_conversation_length": settings.max_conversation_length,
            "model": settings.ai_model,
            "workflow_storage": workflow_stats,
            "test_mode": settings.environment == "test",
            "cache_stats": cache_stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "mcp_server_connected": False,
            "workflow_storage": {"total_workflows": 0, "error": "storage_unavailable"}
        }


@router.get("/telemetry/tokens")
async def get_token_telemetry(
    conversation_id: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get token usage telemetry for monitoring context window consumption.

    Query parameters:
    - conversation_id: Filter by specific conversation (optional)
    - limit: Maximum number of entries to return (default: 10)
    """
    try:
        telemetry_entries = conversation_manager.get_token_telemetry(
            conversation_id=conversation_id,
            limit=limit
        )

        token_stats = conversation_manager.get_token_stats()

        return {
            "telemetry": telemetry_entries,
            "summary": token_stats,
            "metadata": {
                "entries_returned": len(telemetry_entries),
                "filtered_by_conversation": conversation_id is not None,
                "conversation_id": conversation_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telemetry error: {str(e)}")


async def generate_sse_stream(
    message: str,
    conversation_id: str,
    session_id: str,
    workflow_spec_dict: Optional[Dict[str, Any]] = None,
    workflow_source: Optional[str] = None,
    language: str = "en"
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
            user_context={"language": language}
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

                    # Check if workflow was created by looking for creation tools
                    tools_used = event_data.get('mcp_tools_used', [])
                    workflow_created_id = None

                    if 'create_workflow_from_description' in tools_used or 'create_workflow_from_template' in tools_used:
                        # Workflow was created - try to extract ID from response
                        # Look for workflow ID pattern in the complete response
                        import re
                        workflow_id_match = re.search(r'wf_[\w_]+', complete_response)
                        if workflow_id_match:
                            workflow_created_id = workflow_id_match.group(0)
                        else:
                            # Fallback: check recent workflows in storage
                            recent_workflows = workflow_storage.get_stats().get('workflow_ids', [])
                            if recent_workflows:
                                workflow_created_id = recent_workflows[-1]  # Most recent

                    # Handle workflow binding if created
                    binding = chat_binding_manager.get_binding(conversation_id)

                    if workflow_created_id and binding and not binding.is_bound():
                        try:
                            # Fetch and cache the workflow
                            import httpx
                            async with httpx.AsyncClient() as client:
                                response = await client.get(
                                    f"{settings.svc_builder_url}/api/v1/workflows/{workflow_created_id}"
                                )
                                if response.status_code == 200:
                                    workflow_data = response.json()
                                    if "workflow_spec" in workflow_data:
                                        workflow_storage.store_workflow(workflow_created_id, workflow_data["workflow_spec"])
                                        logger.info(f"✅ Stored workflow {workflow_created_id} in streaming cache")

                            # Bind the workflow
                            binding = chat_binding_manager.bind_workflow(conversation_id, workflow_created_id)
                            logger.info(f"✅ Bound streaming chat {conversation_id} to workflow {workflow_created_id}")
                        except Exception as e:
                            logger.error(f"Failed to bind workflow in streaming: {e}")

                    # Get final binding state
                    binding = chat_binding_manager.get_binding(conversation_id)

                    # Add all required fields to completion event
                    event_data['prompt_count'] = prompt_count
                    event_data['session_id'] = session_id
                    event_data['workflow_created_id'] = workflow_created_id
                    event_data['workflow_bound_id'] = binding.bound_workflow_id if binding else None
                    event_data['is_chat_locked'] = binding.is_bound() if binding else False

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

    Now includes session management and chat-to-workflow binding.
    """
    try:
        # 1. Validate session exists
        if not request.session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {request.session_id} not found. Please create a session first."
            )

        # Update session activity
        session_manager.update_activity(request.session_id)

        # 2. Get or create conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # 3. Get or create chat binding
        binding = chat_binding_manager.get_binding(conversation_id)

        if not binding:
            binding = chat_binding_manager.create_binding(conversation_id, request.session_id)
            logger.info(f"Created new chat binding for streaming: {conversation_id}")
        else:
            chat_binding_manager.update_activity(conversation_id)

        # 4. Resolve workflow specification
        workflow_spec_dict = None
        workflow_source = None

        if binding.is_bound():
            # Chat is bound - ALWAYS use bound workflow
            workflow_id = binding.bound_workflow_id
            workflow_spec_dict = workflow_storage.get_workflow(workflow_id)

            if not workflow_spec_dict:
                raise HTTPException(
                    status_code=500,
                    detail=f"Bound workflow {workflow_id} not found"
                )

            workflow_source = f"bound_workflow:{workflow_id}"
            logger.info(f"🔒 Streaming with bound workflow {workflow_id}")

        elif request.workflow_spec:
            if hasattr(request.workflow_spec, 'model_dump'):
                workflow_spec_dict = request.workflow_spec.model_dump()
            else:
                workflow_spec_dict = request.workflow_spec
            workflow_source = "provided_spec"

        elif request.workflow_id:
            workflow_spec_dict = conversation_manager.get_workflow_cached(request.workflow_id)

            if workflow_spec_dict:
                workflow_source = f"cached_workflow:{request.workflow_id}"
            else:
                stored_workflow = workflow_storage.get_workflow(request.workflow_id)
                if stored_workflow is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Workflow with ID '{request.workflow_id}' not found in storage"
                    )
                workflow_spec_dict = stored_workflow
                conversation_manager.cache_workflow(request.workflow_id, workflow_spec_dict)
                workflow_source = f"stored_workflow:{request.workflow_id}"

        # Create the streaming generator
        stream_generator = generate_sse_stream(
            message=request.message,
            conversation_id=conversation_id,
            session_id=request.session_id,
            workflow_spec_dict=workflow_spec_dict,
            workflow_source=workflow_source,
            language=request.language.value
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