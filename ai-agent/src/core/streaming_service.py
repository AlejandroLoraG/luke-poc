"""
Streaming Service for AI Agent Responses

This module provides a clean, robust streaming implementation for AI agent responses
with deduplication, sequence tracking, and comprehensive error handling.
"""

import json
import hashlib
import time
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass

from ..agents.workflow_conversation_agent import WorkflowConversationAgent

logger = logging.getLogger(__name__)


@dataclass
class StreamingMetrics:
    """Metrics for streaming response monitoring."""
    total_chunks: int = 0
    unique_sequences: int = 0
    response_length: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration_ms(self) -> float:
        """Get streaming duration in milliseconds."""
        return (self.end_time - self.start_time) * 1000 if self.end_time > self.start_time else 0.0


@dataclass
class StreamChunk:
    """Represents a single streaming chunk with metadata."""
    content: str
    sequence_id: str
    chunk_number: int
    timestamp: float
    tools_used: List[str]

    def to_sse_event(self, event_type: str = "chunk") -> str:
        """Convert chunk to Server-Sent Event format."""
        data = {
            "type": event_type,
            "content": self.content,
            "sequence_id": self.sequence_id,
            "chunk_count": self.chunk_number,
            "timestamp": self.timestamp
        }
        return f"data: {json.dumps(data)}\n\n"


class StreamingService:
    """
    Service for handling AI agent streaming responses with deduplication and monitoring.

    Features:
    - Content deduplication using hashing
    - Sequence tracking for ordering
    - Streaming metrics collection
    - Robust error handling
    - Clean SSE event generation
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def stream_agent_response(
        self,
        agent: WorkflowConversationAgent,
        message: str,
        workflow_spec: Optional[Dict[str, Any]] = None,
        conversation_history: str = "",
        user_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Tuple[StreamChunk, StreamingMetrics], None]:
        """
        Stream agent response with deduplication and metrics.

        Args:
            agent: The workflow conversation agent
            message: User message to process
            workflow_spec: Optional workflow specification
            conversation_history: Previous conversation context
            user_context: Additional user context

        Yields:
            Tuple of (StreamChunk, StreamingMetrics) for each response chunk
        """
        metrics = StreamingMetrics(start_time=time.time())

        # Deduplication state
        content_hashes = set()
        sequence_counter = 0
        response_parts = []

        try:
            self.logger.info(f"Starting streaming for message: {message[:50]}...")

            async for chunk_content, tools_used, agent_sequence_id in agent.chat_stream(
                message=message,
                workflow_spec=workflow_spec,
                conversation_history=conversation_history,
                user_context=user_context or {}
            ):
                # Skip empty content
                if not chunk_content or not chunk_content.strip():
                    continue

                # Generate content hash for deduplication
                content_hash = hashlib.md5(chunk_content.encode('utf-8')).hexdigest()

                # Skip duplicates
                if content_hash in content_hashes:
                    self.logger.debug(f"Skipping duplicate chunk: {content_hash[:8]}")
                    continue

                content_hashes.add(content_hash)
                sequence_counter += 1

                # Create stream chunk
                chunk = StreamChunk(
                    content=chunk_content,
                    sequence_id=f"stream_{sequence_counter}_{int(time.time() * 1000)}",
                    chunk_number=sequence_counter,
                    timestamp=time.time(),
                    tools_used=tools_used or []
                )

                response_parts.append(chunk_content)

                # Update metrics
                metrics.total_chunks = sequence_counter
                metrics.unique_sequences = len(content_hashes)
                metrics.response_length = len("".join(response_parts))

                self.logger.debug(f"Yielding chunk {sequence_counter}: {chunk_content[:30]}...")
                yield chunk, metrics

        except Exception as e:
            self.logger.error(f"Error in streaming: {str(e)}", exc_info=True)
            # Yield error chunk
            error_chunk = StreamChunk(
                content=f"I encountered an error: {str(e)}",
                sequence_id=f"error_{int(time.time() * 1000)}",
                chunk_number=sequence_counter + 1,
                timestamp=time.time(),
                tools_used=[]
            )
            yield error_chunk, metrics

        finally:
            metrics.end_time = time.time()
            self.logger.info(
                f"Streaming completed: {metrics.total_chunks} chunks, "
                f"{metrics.response_length} chars, {metrics.duration_ms:.1f}ms"
            )

    async def generate_sse_stream(
        self,
        agent: WorkflowConversationAgent,
        message: str,
        conversation_id: str,
        workflow_spec: Optional[Dict[str, Any]] = None,
        workflow_source: Optional[str] = None,
        conversation_history: str = "",
        user_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate complete SSE stream for chat responses.

        Args:
            agent: The workflow conversation agent
            message: User message
            conversation_id: Unique conversation identifier
            workflow_spec: Optional workflow specification
            workflow_source: Source of workflow data
            conversation_history: Previous conversation context
            user_context: Additional user context

        Yields:
            SSE-formatted strings for streaming response
        """
        # Send start event
        start_event = {
            "type": "start",
            "conversation_id": conversation_id,
            "timestamp": time.time()
        }
        yield f"data: {json.dumps(start_event)}\n\n"

        # Track response state
        response_chunks = []
        all_tools_used = []
        final_metrics = None

        try:
            # Stream agent response
            async for chunk, metrics in self.stream_agent_response(
                agent=agent,
                message=message,
                workflow_spec=workflow_spec,
                conversation_history=conversation_history,
                user_context=user_context
            ):
                # Collect response data
                response_chunks.append(chunk.content)
                all_tools_used.extend(chunk.tools_used)
                final_metrics = metrics

                # Send chunk as SSE
                yield chunk.to_sse_event()

            # Send completion event
            completion_event = {
                "type": "complete",
                "conversation_id": conversation_id,
                "workflow_source": workflow_source,
                "streaming_metrics": {
                    "total_chunks": final_metrics.total_chunks if final_metrics else 0,
                    "unique_sequences": final_metrics.unique_sequences if final_metrics else 0,
                    "response_length": final_metrics.response_length if final_metrics else 0,
                    "duration_ms": final_metrics.duration_ms if final_metrics else 0.0
                },
                "mcp_tools_used": list(set(all_tools_used)),  # Remove duplicates
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(completion_event)}\n\n"

        except Exception as e:
            self.logger.error(f"Error in SSE stream generation: {str(e)}", exc_info=True)
            # Send error event
            error_event = {
                "type": "error",
                "error": str(e),
                "conversation_id": conversation_id,
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    @staticmethod
    def create_basic_sse_event(event_type: str, data: Dict[str, Any]) -> str:
        """
        Create a basic SSE event string.

        Args:
            event_type: Type of the event
            data: Event data dictionary

        Returns:
            SSE-formatted string
        """
        event_data = {"type": event_type, **data}
        return f"data: {json.dumps(event_data)}\n\n"


# Global streaming service instance
streaming_service = StreamingService()