"""
Core workflow operations module.

This module contains the basic CRUD operations for workflow management:
- get_workflow: Retrieve a workflow by ID
- list_workflows: List all workflows
- delete_workflow: Delete a workflow
- validate_workflow: Validate workflow structure
"""

from typing import Dict, Any, Optional
from svc_client import svc_client
from shared.schemas import StandardErrorResponse, ErrorCategory, ErrorSeverity, ErrorCodes


def create_success_response(data: Dict[str, Any], operation: str) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {"success": True, "operation": operation, "service": "mcp-server"}
    response.update(data)
    return response


def handle_tool_error(e: Exception, operation: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Handle tool errors with standardized error response."""
    return {
        "success": False,
        "error": str(e),
        "operation": operation,
        "service": "mcp-server",
        "context": context or {}
    }


async def get_workflow(spec_id: str) -> Dict[str, Any]:
    """
    Retrieve a workflow specification by ID.

    Args:
        spec_id: The workflow specification ID to retrieve

    Returns:
        Complete workflow specification with metadata
    """
    try:
        result = await svc_client.get_workflow(spec_id)
        return create_success_response(
            {
                "workflow": result.get("workflow_spec"),
                "metadata": result.get("metadata", {}),
                "spec_id": spec_id
            },
            "get_workflow"
        )
    except Exception as e:
        return handle_tool_error(e, "get_workflow", {"spec_id": spec_id})


async def list_workflows() -> Dict[str, Any]:
    """
    List all available workflow specifications.

    Returns:
        List of workflow summaries with metadata
    """
    try:
        result = await svc_client.list_workflows()
        return create_success_response(
            {
                "workflows": result.get("workflows", []),
                "total_count": result.get("total_count", 0),
                "storage_stats": result.get("storage_stats", {})
            },
            "list_workflows"
        )
    except Exception as e:
        return handle_tool_error(e, "list_workflows", {"workflows": []})


async def delete_workflow(spec_id: str) -> Dict[str, Any]:
    """
    Delete a workflow specification.

    Args:
        spec_id: The workflow specification ID to delete

    Returns:
        Deletion result with success status
    """
    try:
        result = await svc_client.delete_workflow(spec_id)
        return create_success_response(
            {
                "message": f"Workflow '{spec_id}' deleted successfully",
                "spec_id": spec_id,
                "result": result
            },
            "delete_workflow"
        )
    except Exception as e:
        return handle_tool_error(e, "delete_workflow", {"spec_id": spec_id})


async def validate_workflow(spec_id: str) -> Dict[str, Any]:
    """
    Validate a workflow specification structure.

    Args:
        spec_id: The workflow specification ID to validate

    Returns:
        Validation result with any issues found
    """
    try:
        result = await svc_client.validate_workflow(spec_id)
        return create_success_response(
            {
                "spec_id": spec_id,
                "validation_result": result,
                "is_valid": result.get("valid", False),
                "issues": result.get("issues", [])
            },
            "validate_workflow"
        )
    except Exception as e:
        return handle_tool_error(e, "validate_workflow", {"spec_id": spec_id})