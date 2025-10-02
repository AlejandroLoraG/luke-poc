"""
Pydantic schemas for MCP tool parameters.

These schemas ensure Gemini compatibility by using explicit Pydantic models
instead of Dict[str, Any], which Gemini's function calling doesn't support.
"""

from .tool_parameters import (
    WorkflowCustomization,
    PermissionUpdate,
    FormField,
    WorkflowAction,
)

__all__ = [
    "WorkflowCustomization",
    "PermissionUpdate",
    "FormField",
    "WorkflowAction",
]
