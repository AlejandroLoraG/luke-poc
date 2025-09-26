import asyncio
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from config import settings
from svc_client import svc_client


# Create FastMCP server
server = FastMCP(settings.server_name, host="0.0.0.0", port=settings.mcp_server_port)


@server.tool()
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
        return {
            "success": True,
            "workflow": result.get("workflow_spec"),
            "metadata": result.get("metadata", {}),
            "spec_id": spec_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "spec_id": spec_id
        }


@server.tool()
async def list_workflows() -> Dict[str, Any]:
    """
    List all available workflow specifications.

    Returns:
        List of workflow summaries with metadata
    """
    try:
        result = await svc_client.list_workflows()
        return {
            "success": True,
            "workflows": result.get("workflows", []),
            "total_count": result.get("total_count", 0),
            "storage_stats": result.get("storage_stats", {})
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "workflows": []
        }




@server.tool()
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
        return {
            "success": True,
            "message": f"Workflow '{spec_id}' deleted successfully",
            "spec_id": spec_id,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "spec_id": spec_id
        }


@server.tool()
async def validate_workflow(spec_id: str) -> Dict[str, Any]:
    """
    Validate a workflow specification structure.

    Args:
        spec_id: The workflow specification ID to validate

    Returns:
        Validation result with details
    """
    try:
        result = await svc_client.validate_workflow(spec_id)
        return {
            "success": True,
            "valid": result.get("valid", False),
            "message": result.get("message", ""),
            "spec_id": spec_id,
            "validation_details": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "spec_id": spec_id,
            "valid": False
        }


@server.tool()
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

        return {
            "success": True,
            "spec_id": spec_id,
            "states": states,
            "states_count": len(states)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "spec_id": spec_id,
            "states": []
        }


@server.tool()
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

        return {
            "success": True,
            "spec_id": spec_id,
            "actions": actions,
            "actions_count": len(actions)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "spec_id": spec_id,
            "actions": []
        }


@server.tool()
async def create_workflow_from_description(
    name: str,
    description: str,
    states: list,
    actions: list
) -> Dict[str, Any]:
    """
    Create a new workflow from business description with auto-generated technical fields.

    Args:
        name: Business name for the workflow (e.g., "Document Approval Process")
        description: What this workflow does
        states: List of state names in business language (e.g., ["Submitted", "Under Review", "Approved"])
        actions: List of transition descriptions (e.g., ["Submit for review", "Approve request"])

    Returns:
        Success/failure status with workflow details
    """
    try:
        # Auto-generate technical fields from business description
        spec_id = f"wf_{name.lower().replace(' ', '_').replace('-', '_')}"
        slug = name.lower().replace(' ', '_').replace('-', '_')

        # Convert business states to technical format
        workflow_states = []
        for i, state_name in enumerate(states):
            state_slug = state_name.lower().replace(' ', '_').replace('-', '_')
            state_type = "initial" if i == 0 else ("final" if i == len(states) - 1 else "intermediate")
            workflow_states.append({
                "slug": state_slug,
                "name": state_name,
                "type": state_type
            })

        # Convert business actions to technical format
        workflow_actions = []
        workflow_permissions = []

        for i, action_name in enumerate(actions):
            if i < len(states) - 1:  # Create transitions between sequential states
                action_slug = action_name.lower().replace(' ', '_').replace('-', '_')
                permission_slug = f"{action_slug}_perm"

                from_state = workflow_states[i]["slug"]
                to_state = workflow_states[i + 1]["slug"]

                workflow_actions.append({
                    "slug": action_slug,
                    "from": from_state,
                    "to": to_state,
                    "requiresForm": False,
                    "permission": permission_slug
                })

                workflow_permissions.append({
                    "slug": permission_slug,
                    "description": f"Permission to {action_name.lower()}"
                })

        # Create complete workflow specification
        workflow_spec = {
            "specId": spec_id,
            "specVersion": 1,
            "tenantId": "luke_123",
            "name": name,
            "slug": slug,
            "states": workflow_states,
            "actions": workflow_actions,
            "permissions": workflow_permissions,
            "automations": []
        }

        # Use existing create workflow endpoint
        result = await svc_client.create_workflow(workflow_spec)

        return {
            "success": True,
            "workflow_id": spec_id,
            "name": name,
            "states_created": len(workflow_states),
            "actions_created": len(workflow_actions),
            "message": f"Successfully created {name} workflow with {len(workflow_states)} states"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create workflow: {str(e)}",
            "workflow_id": None
        }


@server.tool()
async def add_workflow_state(
    workflow_id: str,
    state_name: str,
    state_position: str = "end"
) -> Dict[str, Any]:
    """
    Add a new state to an existing workflow.

    Args:
        workflow_id: The workflow to modify
        state_name: Business name for the new state
        state_position: Where to add it ("start", "end", or "after:state_slug")

    Returns:
        Success/failure status
    """
    try:
        # Get existing workflow
        workflow_data = await svc_client.get_workflow(workflow_id)
        workflow_spec = workflow_data["workflow_spec"]

        # Create new state
        state_slug = state_name.lower().replace(' ', '_').replace('-', '_')
        new_state = {
            "slug": state_slug,
            "name": state_name,
            "type": "intermediate"  # Default to intermediate, will be updated if needed
        }

        # Add state at requested position
        states = workflow_spec["states"]
        if state_position == "start":
            states.insert(0, new_state)
            # Update state types
            states[0]["type"] = "initial"
            if len(states) > 1:
                states[1]["type"] = "intermediate"
        elif state_position == "end":
            states.append(new_state)
            # Update state types
            if len(states) > 1:
                states[-2]["type"] = "intermediate"
            states[-1]["type"] = "final"

        # Update workflow
        result = await svc_client.update_workflow(workflow_id, workflow_spec)

        return {
            "success": True,
            "state_added": state_name,
            "state_slug": state_slug,
            "total_states": len(states)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to add state: {str(e)}"
        }


@server.tool()
async def update_workflow_actions(
    workflow_id: str,
    action_descriptions: list
) -> Dict[str, Any]:
    """
    Update workflow actions based on business descriptions.

    Args:
        workflow_id: The workflow to modify
        action_descriptions: List of action descriptions (e.g., ["Submit request", "Approve"])

    Returns:
        Success/failure status
    """
    try:
        # Get existing workflow
        workflow_data = await svc_client.get_workflow(workflow_id)
        workflow_spec = workflow_data["workflow_spec"]

        states = workflow_spec["states"]
        new_actions = []
        new_permissions = []

        # Create actions between sequential states
        for i, action_desc in enumerate(action_descriptions):
            if i < len(states) - 1:
                action_slug = action_desc.lower().replace(' ', '_').replace('-', '_')
                permission_slug = f"{action_slug}_perm"

                new_actions.append({
                    "slug": action_slug,
                    "from": states[i]["slug"],
                    "to": states[i + 1]["slug"],
                    "requiresForm": False,
                    "permission": permission_slug
                })

                new_permissions.append({
                    "slug": permission_slug,
                    "description": f"Permission to {action_desc.lower()}"
                })

        # Update workflow with new actions and permissions
        workflow_spec["actions"] = new_actions
        workflow_spec["permissions"] = new_permissions

        result = await svc_client.update_workflow(workflow_id, workflow_spec)

        return {
            "success": True,
            "actions_updated": len(new_actions),
            "permissions_created": len(new_permissions)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update actions: {str(e)}"
        }


@server.tool()
async def create_workflow_from_template(
    workflow_name: str,
    template_type: str,
    customizations: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a workflow from a predefined template.

    Args:
        workflow_name: Business name for the workflow
        template_type: Type of template (approval, incident, task, document_review, request_handling)
        customizations: Optional customizations to the template

    Returns:
        Created workflow details
    """
    try:
        templates = {
            "approval": {
                "description": "Standard approval process",
                "states": ["Submitted", "Under Review", "Approved"],
                "actions": ["Submit for Review", "Approve Request"]
            },
            "incident": {
                "description": "Incident management process",
                "states": ["Reported", "Under Investigation", "Resolved"],
                "actions": ["Start Investigation", "Mark Resolved"]
            },
            "task": {
                "description": "Task management process",
                "states": ["Created", "In Progress", "Completed"],
                "actions": ["Start Work", "Complete Task"]
            },
            "document_review": {
                "description": "Document review and publication process",
                "states": ["Draft", "Under Review", "Published"],
                "actions": ["Submit for Review", "Publish Document"]
            },
            "request_handling": {
                "description": "General request processing",
                "states": ["Submitted", "Processing", "Fulfilled"],
                "actions": ["Begin Processing", "Fulfill Request"]
            }
        }

        if template_type not in templates:
            return {
                "success": False,
                "error": f"Unknown template type: {template_type}. Available: {list(templates.keys())}",
                "available_templates": list(templates.keys())
            }

        template = templates[template_type]

        # Apply customizations if provided
        states = customizations.get("states", template["states"]) if customizations else template["states"]
        actions = customizations.get("actions", template["actions"]) if customizations else template["actions"]
        description = customizations.get("description", template["description"]) if customizations else template["description"]

        # Use the existing create_workflow_from_description tool
        result = await create_workflow_from_description(
            name=workflow_name,
            description=description,
            states=states,
            actions=actions
        )

        if result["success"]:
            result["template_used"] = template_type
            result["template_description"] = description

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create workflow from template: {str(e)}",
            "available_templates": list(templates.keys())
        }


@server.tool()
async def get_workflow_templates() -> Dict[str, Any]:
    """
    Get available workflow templates with descriptions.

    Returns:
        Available workflow templates and their descriptions
    """
    templates = {
        "approval": {
            "name": "Approval Process",
            "description": "Standard approval workflow with submission, review, and decision stages",
            "typical_states": ["Submitted", "Under Review", "Approved/Rejected"],
            "use_cases": ["Document approval", "Request approval", "Budget approval"]
        },
        "incident": {
            "name": "Incident Management",
            "description": "Process for handling and resolving incidents",
            "typical_states": ["Reported", "Under Investigation", "Resolved"],
            "use_cases": ["IT incidents", "Customer complaints", "Safety incidents"]
        },
        "task": {
            "name": "Task Management",
            "description": "Simple task tracking from creation to completion",
            "typical_states": ["Created", "In Progress", "Completed"],
            "use_cases": ["Project tasks", "Maintenance tasks", "Work assignments"]
        },
        "document_review": {
            "name": "Document Review",
            "description": "Document lifecycle from draft to publication",
            "typical_states": ["Draft", "Under Review", "Published"],
            "use_cases": ["Content creation", "Policy documents", "Reports"]
        },
        "request_handling": {
            "name": "Request Processing",
            "description": "General request processing workflow",
            "typical_states": ["Submitted", "Processing", "Fulfilled"],
            "use_cases": ["Service requests", "Support tickets", "Resource requests"]
        }
    }

    return {
        "success": True,
        "templates": templates,
        "total_templates": len(templates)
    }


@server.tool()
async def check_svc_builder_health() -> Dict[str, Any]:
    """
    Check the health status of the svc-builder service.

    Returns:
        Health status and connection information
    """
    try:
        result = await svc_client.health_check()
        return {
            "success": True,
            "svc_builder_status": "healthy",
            "svc_builder_url": settings.svc_builder_url,
            "health_details": result
        }
    except Exception as e:
        return {
            "success": False,
            "svc_builder_status": "unhealthy",
            "svc_builder_url": settings.svc_builder_url,
            "error": str(e)
        }


if __name__ == "__main__":
    # Run the MCP server
    print(f"Starting {settings.server_name} on port {settings.mcp_server_port}")
    print(f"Connecting to svc-builder at: {settings.svc_builder_url}")

    # Test the svc-builder connection first
    try:
        import asyncio
        async def test_connection():
            health = await svc_client.health_check()
            print(f"svc-builder connection test: {health}")

        asyncio.run(test_connection())
    except Exception as e:
        print(f"Warning: Could not connect to svc-builder: {e}")

    # Use FastMCP's built-in HTTP transport (SSE - Server-Sent Events)
    print("Starting FastMCP server with HTTP/SSE transport...")
    server.run(
        transport="streamable-http"
    )