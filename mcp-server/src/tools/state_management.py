"""
Workflow state and action management module.

This module handles workflow state and action operations:
- get_workflow_states: Retrieve workflow states
- get_workflow_actions: Retrieve workflow actions
- add_workflow_state: Add new state to workflow
- update_workflow_actions: Update workflow actions
"""

from typing import Dict, Any, List, Optional
from svc_client import svc_client
from shared.schemas import StandardErrorResponse, ErrorCategory, ErrorSeverity, ErrorCodes
from schemas.tool_parameters import WorkflowAction


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


async def get_workflow_states(spec_id: str) -> Dict[str, Any]:
    """
    Get the states of a specific workflow.

    Args:
        spec_id: The workflow specification ID

    Returns:
        List of workflow states with their properties
    """
    try:
        workflow_result = await svc_client.get_workflow(spec_id)
        workflow_spec = workflow_result.get("workflow_spec", {})
        states = workflow_spec.get("states", [])

        return create_success_response(
            {
                "spec_id": spec_id,
                "states": states,
                "states_count": len(states)
            },
            "get_workflow_states"
        )
    except Exception as e:
        return handle_tool_error(e, "get_workflow_states", {"spec_id": spec_id, "states": []})


async def get_workflow_actions(spec_id: str) -> Dict[str, Any]:
    """
    Get the actions of a specific workflow.

    Args:
        spec_id: The workflow specification ID

    Returns:
        List of workflow actions with their properties
    """
    try:
        workflow_result = await svc_client.get_workflow(spec_id)
        workflow_spec = workflow_result.get("workflow_spec", {})
        actions = workflow_spec.get("actions", [])

        return create_success_response(
            {
                "spec_id": spec_id,
                "actions": actions,
                "actions_count": len(actions)
            },
            "get_workflow_actions"
        )
    except Exception as e:
        return handle_tool_error(e, "get_workflow_actions", {"spec_id": spec_id, "actions": []})


async def add_workflow_state(
    spec_id: str,
    state_name: str,
    is_final: bool = False,
    requires_approval: bool = False,
    permissions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Add a new state to an existing workflow.

    Args:
        spec_id: The workflow specification ID
        state_name: Human-readable state name (e.g., "Under Review")
        is_final: Whether this is a terminal state
        requires_approval: Whether this state requires approval
        permissions: List of permissions required for this state

    Returns:
        Success/failure status with updated workflow details
    """
    try:
        # Get current workflow
        workflow_result = await svc_client.get_workflow(spec_id)
        workflow_spec = workflow_result.get("workflow_spec", {})

        # Create state ID from name
        state_id = state_name.lower().replace(" ", "_").replace("-", "_")

        # Create new state
        new_state = {
            "id": state_id,
            "name": state_name,
            "type": "end" if is_final else "intermediate",
            "metadata": {
                "requires_approval": requires_approval,
                "permissions": permissions or []
            }
        }

        # Add to states list
        current_states = workflow_spec.get("states", [])
        current_states.append(new_state)
        workflow_spec["states"] = current_states

        # Update workflow
        update_result = await svc_client.update_workflow(spec_id, workflow_spec)

        return create_success_response(
            {
                "spec_id": spec_id,
                "new_state": new_state,
                "total_states": len(current_states),
                "update_result": update_result
            },
            "add_workflow_state"
        )
    except Exception as e:
        return handle_tool_error(e, "add_workflow_state", {"spec_id": spec_id, "state_name": state_name})


async def update_workflow_actions(
    spec_id: str,
    actions: List[WorkflowAction]
) -> Dict[str, Any]:
    """
    Update the actions for a specific workflow.

    Args:
        spec_id: The workflow specification ID
        actions: List of WorkflowAction objects (Pydantic models for Gemini compatibility)

    Returns:
        Success/failure status with updated workflow details
    """
    try:
        # Get current workflow
        workflow_result = await svc_client.get_workflow(spec_id)
        workflow_spec = workflow_result.get("workflow_spec", {})

        # Convert Pydantic models to dict format for API
        actions_data = [action.model_dump(by_alias=True) for action in actions]

        # Update actions
        workflow_spec["actions"] = actions_data

        # Save updated workflow
        update_result = await svc_client.update_workflow(spec_id, workflow_spec)

        return create_success_response(
            {
                "spec_id": spec_id,
                "actions": actions_data,
                "actions_count": len(actions),
                "update_result": update_result
            },
            "update_workflow_actions"
        )
    except Exception as e:
        return handle_tool_error(e, "update_workflow_actions", {"spec_id": spec_id})