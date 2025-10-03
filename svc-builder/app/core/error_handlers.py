"""
Error handling middleware and utilities for svc-builder service.

This module provides standardized error handling patterns using
the shared error schemas for consistent responses.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from shared.schemas import (
    StandardErrorResponse,
    ValidationErrorResponse,
    NotFoundErrorResponse,
    InternalErrorResponse,
    ErrorCategory,
    ErrorSeverity,
    ErrorCodes,
    ERROR_CATEGORY_TO_HTTP_STATUS
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for svc-builder service."""

    @staticmethod
    def create_error_response(
        error: str,
        operation: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: str = ErrorCodes.OPERATION_FAILED,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ) -> StandardErrorResponse:
        """
        Create a standardized error response.

        Args:
            error: Error message
            operation: Description of the failed operation
            category: Error category for classification
            severity: Error severity level
            error_code: Machine-readable error code
            context: Optional context information
            suggestion: Optional user guidance

        Returns:
            StandardErrorResponse instance
        """
        request_id = str(uuid.uuid4())

        return StandardErrorResponse(
            error=error,
            error_code=error_code,
            category=category,
            severity=severity,
            service="svc-builder",
            operation=operation,
            request_id=request_id,
            context=context,
            suggestion=suggestion
        )

    @staticmethod
    def workflow_not_found_error(workflow_id: str, operation: str = "get_workflow") -> NotFoundErrorResponse:
        """Create a standardized workflow not found error."""
        return NotFoundErrorResponse(
            error=f"Workflow with ID '{workflow_id}' not found",
            error_code=ErrorCodes.WORKFLOW_NOT_FOUND,
            service="svc-builder",
            operation=operation,
            request_id=str(uuid.uuid4()),
            context={"workflow_id": workflow_id},
            suggestion="Check that the workflow ID is correct and the workflow exists in storage"
        )

    @staticmethod
    def validation_error(message: str, field: str, operation: str, value: Any = None) -> ValidationErrorResponse:
        """Create a standardized validation error."""
        return ValidationErrorResponse(
            error=message,
            error_code=ErrorCodes.INVALID_INPUT,
            service="svc-builder",
            operation=operation,
            request_id=str(uuid.uuid4()),
            context={"field": field, "value": value},
            suggestion="Please provide valid input according to the API specification"
        )

    @staticmethod
    def internal_error(error: str, operation: str, context: Optional[Dict[str, Any]] = None) -> InternalErrorResponse:
        """Create a standardized internal server error."""
        return InternalErrorResponse(
            error=error,
            error_code=ErrorCodes.INTERNAL_ERROR,
            service="svc-builder",
            operation=operation,
            request_id=str(uuid.uuid4()),
            context=context,
            suggestion="Please try again later or contact support if the problem persists"
        )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.

    Args:
        request: FastAPI request object
        exc: The unhandled exception

    Returns:
        JSONResponse with standardized error format
    """
    request_id = str(uuid.uuid4())
    operation = f"{request.method} {request.url.path}"

    # Log the error with full context
    logger.error(
        f"Unhandled exception in {operation}: {str(exc)}",
        extra={
            "request_id": request_id,
            "operation": operation,
            "exception_type": type(exc).__name__,
            "request_method": request.method,
            "request_path": str(request.url.path),
            "request_query": str(request.url.query) if request.url.query else None,
        },
        exc_info=True
    )

    # Create standardized error response
    error_response = ErrorHandler.internal_error(
        error="An unexpected error occurred",
        operation=operation,
        context={
            "exception_type": type(exc).__name__,
            "request_method": request.method,
            "request_path": str(request.url.path)
        }
    )

    status_code = ERROR_CATEGORY_TO_HTTP_STATUS[error_response.category]

    import json
    return JSONResponse(
        status_code=status_code,
        content=json.loads(error_response.model_dump_json())
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for HTTP exceptions to provide standardized error format.

    Args:
        request: FastAPI request object
        exc: The HTTP exception

    Returns:
        JSONResponse with standardized error format
    """
    operation = f"{request.method} {request.url.path}"

    # Map HTTP status to error category
    category = ErrorCategory.INTERNAL
    if exc.status_code == 400:
        category = ErrorCategory.VALIDATION
    elif exc.status_code == 401:
        category = ErrorCategory.AUTHENTICATION
    elif exc.status_code == 403:
        category = ErrorCategory.AUTHORIZATION
    elif exc.status_code == 404:
        category = ErrorCategory.NOT_FOUND
    elif exc.status_code == 409:
        category = ErrorCategory.CONFLICT
    elif exc.status_code == 429:
        category = ErrorCategory.RATE_LIMIT

    # Create standardized error response
    error_response = ErrorHandler.create_error_response(
        error=exc.detail,
        operation=operation,
        category=category,
        error_code=f"HTTP_{exc.status_code}",
        context={
            "status_code": exc.status_code,
            "request_method": request.method,
            "request_path": str(request.url.path)
        }
    )

    import json
    return JSONResponse(
        status_code=exc.status_code,
        content=json.loads(error_response.model_dump_json())
    )