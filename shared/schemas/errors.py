"""
Standardized error response schemas for all services.

This module provides consistent error handling patterns and response formats
across the entire chat-agent system.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorSeverity(str, Enum):
    """Standard error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Standard error categories for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    INTERNAL = "internal"
    TIMEOUT = "timeout"
    NETWORK = "network"


class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = Field(None, description="Field that caused the error (for validation errors)")
    code: str = Field(..., description="Specific error code")
    message: str = Field(..., description="Human-readable error message")
    value: Optional[Any] = Field(None, description="Value that caused the error")


class StandardErrorResponse(BaseModel):
    """
    Standardized error response format for all services.

    This provides a consistent structure for error responses across
    ai-agent, mcp-server, and svc-builder services.
    """
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Primary error message")
    error_code: str = Field(..., description="Machine-readable error code")
    category: ErrorCategory = Field(..., description="Error category for classification")
    severity: ErrorSeverity = Field(ErrorSeverity.MEDIUM, description="Error severity level")

    # Context information
    service: str = Field(..., description="Service that generated the error")
    operation: Optional[str] = Field(None, description="Operation that failed")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    # Additional details
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")

    # User guidance
    suggestion: Optional[str] = Field(None, description="Suggested action for the user")
    documentation_url: Optional[str] = Field(None, description="Link to relevant documentation")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationErrorResponse(StandardErrorResponse):
    """Specialized error response for validation errors."""
    category: Literal[ErrorCategory.VALIDATION] = Field(ErrorCategory.VALIDATION, description="Error category is always validation")
    severity: ErrorSeverity = Field(ErrorSeverity.LOW, description="Validation errors are typically low severity")


class NotFoundErrorResponse(StandardErrorResponse):
    """Specialized error response for resource not found errors."""
    category: Literal[ErrorCategory.NOT_FOUND] = Field(ErrorCategory.NOT_FOUND, description="Error category is always not_found")
    severity: ErrorSeverity = Field(ErrorSeverity.LOW, description="Not found errors are typically low severity")


class InternalErrorResponse(StandardErrorResponse):
    """Specialized error response for internal server errors."""
    category: Literal[ErrorCategory.INTERNAL] = Field(ErrorCategory.INTERNAL, description="Error category is always internal")
    severity: ErrorSeverity = Field(ErrorSeverity.HIGH, description="Internal errors are high severity")


class ExternalServiceErrorResponse(StandardErrorResponse):
    """Specialized error response for external service errors."""
    category: Literal[ErrorCategory.EXTERNAL_SERVICE] = Field(ErrorCategory.EXTERNAL_SERVICE, description="Error category is always external_service")
    severity: ErrorSeverity = Field(ErrorSeverity.MEDIUM, description="External service errors vary in severity")


# HTTP Status Code mappings
ERROR_CATEGORY_TO_HTTP_STATUS = {
    ErrorCategory.VALIDATION: 400,
    ErrorCategory.AUTHENTICATION: 401,
    ErrorCategory.AUTHORIZATION: 403,
    ErrorCategory.NOT_FOUND: 404,
    ErrorCategory.CONFLICT: 409,
    ErrorCategory.RATE_LIMIT: 429,
    ErrorCategory.EXTERNAL_SERVICE: 502,
    ErrorCategory.INTERNAL: 500,
    ErrorCategory.TIMEOUT: 504,
    ErrorCategory.NETWORK: 503,
}


# Common error codes
class ErrorCodes:
    """Standard error codes used across services."""

    # Validation
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Resources
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"

    # Operations
    OPERATION_FAILED = "OPERATION_FAILED"
    WORKFLOW_CREATION_FAILED = "WORKFLOW_CREATION_FAILED"
    WORKFLOW_UPDATE_FAILED = "WORKFLOW_UPDATE_FAILED"

    # External services
    MCP_SERVER_UNAVAILABLE = "MCP_SERVER_UNAVAILABLE"
    SVC_BUILDER_UNAVAILABLE = "SVC_BUILDER_UNAVAILABLE"
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"

    # Internal
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"