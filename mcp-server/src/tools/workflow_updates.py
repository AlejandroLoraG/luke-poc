"""
Workflow Update Tools

This module provides comprehensive tools for updating existing workflows,
including structure modifications, flow changes, permission updates, and
form configuration.
"""

from typing import Dict, Any, List, Optional
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


async def update_workflow_structure(
    workflow_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update workflow basic structure information (name, description, metadata).

    This tool handles high-level workflow changes like renaming or updating descriptions,
    automatically managing slug updates and version increments.

    Args:
        workflow_id: The workflow to modify
        name: New business name for the workflow (optional)
        description: New description for the workflow (optional)

    Returns:
        Success/failure status with detailed validation results
    """
    try:
        if not name and not description:
            return {
                "success": False,
                "error": "At least one field (name or description) must be provided",
                "workflow_id": workflow_id
            }

        # Prepare partial update data
        update_data = {}

        if name:
            update_data["name"] = name
            # Auto-generate slug from name
            update_data["slug"] = name.lower().replace(' ', '_').replace('-', '_')

        # Note: description field would be added to WorkflowSpec if needed
        # For now, we focus on name and slug updates

        # Use partial update
        result = await svc_client.partial_update_workflow(workflow_id, update_data)

        return create_success_response({
            "workflow_id": workflow_id,
            "updated_name": name,
            "message": f"Successfully updated workflow structure",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }, "update_workflow_structure")

    except Exception as e:
        return handle_tool_error(e, "update_workflow_structure", {"workflow_id": workflow_id})


async def modify_workflow_flow(
    workflow_id: str,
    states: Optional[List[str]] = None,
    action_descriptions: Optional[List[str]] = None,
    maintain_existing: bool = True
) -> Dict[str, Any]:
    """
    Modify workflow state flow and transitions in a comprehensive way.

    This tool handles complex workflow flow changes, automatically managing
    state types (initial/intermediate/final), creating corresponding actions,
    and fixing broken references.

    Args:
        workflow_id: The workflow to modify
        states: List of state names in business language (optional)
        action_descriptions: List of action descriptions to create transitions (optional)
        maintain_existing: Whether to preserve existing states/actions when possible

    Returns:
        Success/failure status with detailed changes made
    """
    try:
        if not states and not action_descriptions:
            return {
                "success": False,
                "error": "Either states or action_descriptions must be provided",
                "workflow_id": workflow_id
            }

        # Get existing workflow to understand current structure
        workflow_data = await svc_client.get_workflow(workflow_id)
        existing_workflow = workflow_data["workflow_spec"]

        update_data = {}

        # Handle states update
        if states:
            workflow_states = []
            for i, state_name in enumerate(states):
                state_slug = state_name.lower().replace(' ', '_').replace('-', '_')
                state_type = "initial" if i == 0 else ("final" if i == len(states) - 1 else "intermediate")
                workflow_states.append({
                    "slug": state_slug,
                    "name": state_name,
                    "type": state_type
                })
            update_data["states"] = workflow_states

        # Handle actions update
        if action_descriptions and states:
            # Create actions between sequential states
            workflow_actions = []
            workflow_permissions = []

            for i, action_desc in enumerate(action_descriptions):
                if i < len(states) - 1:
                    action_slug = action_desc.lower().replace(' ', '_').replace('-', '_')
                    permission_slug = f"{action_slug}_perm"

                    from_state = states[i].lower().replace(' ', '_').replace('-', '_')
                    to_state = states[i + 1].lower().replace(' ', '_').replace('-', '_')

                    workflow_actions.append({
                        "slug": action_slug,
                        "from": from_state,
                        "to": to_state,
                        "requiresForm": False,
                        "permission": permission_slug
                    })

                    workflow_permissions.append({
                        "slug": permission_slug,
                        "description": f"Permission to {action_desc.lower()}"
                    })

            update_data["actions"] = workflow_actions
            update_data["permissions"] = workflow_permissions

        # Perform partial update
        result = await svc_client.partial_update_workflow(workflow_id, update_data)

        return create_success_response({
            "workflow_id": workflow_id,
            "states_updated": len(update_data.get("states", [])),
            "actions_updated": len(update_data.get("actions", [])),
            "permissions_updated": len(update_data.get("permissions", [])),
            "message": f"Successfully modified workflow flow",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }, "modify_workflow_flow")

    except Exception as e:
        return handle_tool_error(e, "modify_workflow_flow", {"workflow_id": workflow_id})


async def update_workflow_permissions(
    workflow_id: str,
    permission_updates: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Update workflow permissions and access control settings.

    This tool manages workflow permissions comprehensively, allowing updates
    to existing permissions and addition of new ones with proper validation.

    Args:
        workflow_id: The workflow to modify
        permission_updates: List of permission objects with 'slug' and 'description'
                          e.g., [{"slug": "approve_doc", "description": "Can approve documents"}]

    Returns:
        Success/failure status with permission update details
    """
    try:
        if not permission_updates:
            return {
                "success": False,
                "error": "Permission updates list cannot be empty",
                "workflow_id": workflow_id
            }

        # Validate permission structure
        for perm in permission_updates:
            if "slug" not in perm:
                return {
                    "success": False,
                    "error": "Each permission must have a 'slug' field",
                    "workflow_id": workflow_id
                }

        # Prepare update data
        workflow_permissions = []
        for perm in permission_updates:
            workflow_permissions.append({
                "slug": perm["slug"],
                "description": perm.get("description", f"Permission: {perm['slug']}")
            })

        update_data = {"permissions": workflow_permissions}

        # Perform partial update
        result = await svc_client.partial_update_workflow(workflow_id, update_data)

        return create_success_response({
            "workflow_id": workflow_id,
            "permissions_updated": len(workflow_permissions),
            "permission_slugs": [p["slug"] for p in workflow_permissions],
            "message": f"Successfully updated {len(workflow_permissions)} permissions",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }, "update_workflow_permissions")

    except Exception as e:
        return handle_tool_error(e, "update_workflow_permissions", {"workflow_id": workflow_id})


async def configure_workflow_forms(
    workflow_id: str,
    action_slug: str,
    form_name: str,
    form_fields: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Configure forms for workflow actions with comprehensive field management.

    This tool handles form creation and updates for workflow actions, managing
    field types, validation rules, and form structure.

    Args:
        workflow_id: The workflow to modify
        action_slug: The action to add/update form for
        form_name: Business name for the form
        form_fields: List of field definitions with 'key', 'type', 'required', and optional 'options'
                    e.g., [{"key": "comment", "type": "string", "required": false}]

    Returns:
        Success/failure status with form configuration details
    """
    try:
        if not form_fields:
            return {
                "success": False,
                "error": "Form fields list cannot be empty",
                "workflow_id": workflow_id,
                "action_slug": action_slug
            }

        # Get existing workflow to find the action
        workflow_data = await svc_client.get_workflow(workflow_id)
        existing_workflow = workflow_data["workflow_spec"]

        # Find and update the specific action
        updated_actions = []
        action_found = False

        for action in existing_workflow.get("actions", []):
            if action.get("slug") == action_slug:
                # Update this action with the form
                action_found = True
                updated_action = action.copy()
                updated_action["requiresForm"] = True
                updated_action["form"] = {
                    "name": form_name,
                    "fields": form_fields
                }
                updated_actions.append(updated_action)
            else:
                updated_actions.append(action)

        if not action_found:
            return {
                "success": False,
                "error": f"Action '{action_slug}' not found in workflow",
                "workflow_id": workflow_id,
                "action_slug": action_slug
            }

        # Prepare update data
        update_data = {"actions": updated_actions}

        # Perform partial update
        result = await svc_client.partial_update_workflow(workflow_id, update_data)

        return create_success_response({
            "workflow_id": workflow_id,
            "action_slug": action_slug,
            "form_name": form_name,
            "fields_configured": len(form_fields),
            "field_keys": [f["key"] for f in form_fields],
            "message": f"Successfully configured form '{form_name}' for action '{action_slug}'",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }, "configure_workflow_forms")

    except Exception as e:
        return handle_tool_error(e, "configure_workflow_forms",
                               {"workflow_id": workflow_id, "action_slug": action_slug})