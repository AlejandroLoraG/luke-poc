"""
Error handling utilities for ai-agent service.

This module provides standardized error handling patterns for
conversation and workflow-related operations.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from shared.schemas import (
    StandardErrorResponse,
    InternalErrorResponse,
    ExternalServiceErrorResponse,
    ErrorCategory,
    ErrorSeverity,
    ErrorCodes
)

logger = logging.getLogger(__name__)


class ConversationErrorHandler:
    """Specialized error handling for conversation operations."""

    @staticmethod
    def create_conversation_error(
        error: str,
        operation: str,
        conversation_id: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: str = ErrorCodes.OPERATION_FAILED,
        suggestion: Optional[str] = None
    ) -> StandardErrorResponse:
        """
        Create a standardized conversation error response.

        Args:
            error: Error message
            operation: Description of the failed operation
            conversation_id: ID of the conversation (if applicable)
            category: Error category for classification
            severity: Error severity level
            error_code: Machine-readable error code
            suggestion: Optional user guidance

        Returns:
            StandardErrorResponse instance
        """
        request_id = str(uuid.uuid4())
        context = {"conversation_id": conversation_id} if conversation_id else None

        return StandardErrorResponse(
            error=error,
            error_code=error_code,
            category=category,
            severity=severity,
            service="ai-agent",
            operation=operation,
            request_id=request_id,
            context=context,
            suggestion=suggestion
        )

    @staticmethod
    def mcp_server_error(
        error: str,
        operation: str,
        conversation_id: Optional[str] = None
    ) -> ExternalServiceErrorResponse:
        """Create a standardized MCP server error."""
        return ExternalServiceErrorResponse(
            error=f"MCP Server error: {error}",
            error_code=ErrorCodes.MCP_SERVER_UNAVAILABLE,
            service="ai-agent",
            operation=operation,
            request_id=str(uuid.uuid4()),
            context={
                "conversation_id": conversation_id,
                "external_service": "mcp-server"
            },
            suggestion="The MCP server may be temporarily unavailable. Please try again in a moment."
        )

    @staticmethod
    def ai_service_error(
        error: str,
        operation: str,
        conversation_id: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None
    ) -> ExternalServiceErrorResponse:
        """Create a standardized AI service error."""
        context = {"conversation_id": conversation_id}
        if model_info:
            context.update(model_info)

        return ExternalServiceErrorResponse(
            error=f"AI Service error: {error}",
            error_code=ErrorCodes.AI_SERVICE_ERROR,
            service="ai-agent",
            operation=operation,
            request_id=str(uuid.uuid4()),
            context=context,
            suggestion="The AI service may be experiencing issues. Please try again or simplify your request."
        )

    @staticmethod
    def conversation_limit_error(
        conversation_id: str,
        max_length: int,
        operation: str = "chat"
    ) -> StandardErrorResponse:
        """Create a conversation length limit error."""
        return StandardErrorResponse(
            error=f"Conversation has reached the maximum length of {max_length} turns",
            error_code="CONVERSATION_LIMIT_REACHED",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            service="ai-agent",
            operation=operation,
            request_id=str(uuid.uuid4()),
            context={
                "conversation_id": conversation_id,
                "max_length": max_length
            },
            suggestion="Start a new conversation to continue chatting"
        )

    @staticmethod
    def workflow_context_error(
        error: str,
        workflow_id: Optional[str] = None,
        operation: str = "chat"
    ) -> StandardErrorResponse:
        """Create a workflow context error."""
        return StandardErrorResponse(
            error=f"Workflow context error: {error}",
            error_code="WORKFLOW_CONTEXT_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            service="ai-agent",
            operation=operation,
            request_id=str(uuid.uuid4()),
            context={"workflow_id": workflow_id} if workflow_id else None,
            suggestion="Check that the workflow ID is valid and the workflow exists"
        )


def log_conversation_error(
    error: Exception,
    operation: str,
    conversation_id: Optional[str] = None,
    user_message: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log conversation errors with structured context.

    Args:
        error: The exception that occurred
        operation: Description of the operation that failed
        conversation_id: ID of the conversation (if applicable)
        user_message: User message that caused the error (if applicable)
        extra_context: Additional context information
    """
    log_context = {
        "operation": operation,
        "error_type": type(error).__name__,
        "conversation_id": conversation_id,
    }

    if user_message:
        log_context["user_message_length"] = len(user_message)
        log_context["user_message_preview"] = user_message[:100] + "..." if len(user_message) > 100 else user_message

    if extra_context:
        log_context.update(extra_context)

    logger.error(
        f"Conversation error in {operation}: {str(error)}",
        extra=log_context,
        exc_info=True
    )