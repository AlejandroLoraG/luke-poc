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
        # Intelligent workflow naming and alias generation
        # Create predictable, searchable workflow IDs with multiple patterns
        name_normalized = name.lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('\\', '_')

        # Generate multiple ID patterns for better discoverability
        spec_id_patterns = [
            f"wf_{name_normalized}",
            f"{name_normalized}_workflow",
            f"my_{name_normalized}",
            f"wf_{name_normalized}_process"
        ]

        # Use the first pattern as primary, but track others as aliases
        spec_id = spec_id_patterns[0]
        slug = name_normalized

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
            "message": f"Successfully created '{name}' workflow with {len(workflow_states)} states",
            "discovery_info": {
                "primary_name": name,
                "spec_id": spec_id,
                "searchable_terms": [
                    name,
                    name.lower(),
                    name_normalized.replace('_', ' '),
                    slug
                ],
                "id_patterns": spec_id_patterns[:3],  # Don't expose all patterns
                "creation_hint": f"You can find this workflow by searching for '{name}' or any variation of the name"
            }
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

        # Template name normalization - handle common variations and aliases
        template_aliases = {
            "task_management": "task",
            "task_manager": "task",
            "task_tracking": "task",
            "tasks": "task",
            "document_approval": "approval",
            "approvals": "approval",
            "approve": "approval",
            "incident_management": "incident",
            "incidents": "incident",
            "issue_tracking": "incident",
            "document_reviews": "document_review",
            "documents": "document_review",
            "request_processing": "request_handling",
            "requests": "request_handling",
            "service_requests": "request_handling"
        }

        # Normalize the template type
        normalized_template_type = template_aliases.get(template_type.lower(), template_type.lower())

        if normalized_template_type not in templates:
            return {
                "success": False,
                "error": f"Unknown template type: '{template_type}' (normalized to '{normalized_template_type}'). Available: {list(templates.keys())}",
                "available_templates": list(templates.keys()),
                "template_aliases": template_aliases,
                "suggestion": f"Did you mean one of: {', '.join(templates.keys())}?"
            }

        template = templates[normalized_template_type]

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
            result["template_used"] = normalized_template_type
            result["template_description"] = description

            # Add discoverable information for better workflow tracking
            result["workflow_discovery_info"] = {
                "workflow_name": workflow_name,
                "template_type": normalized_template_type,
                "original_request": template_type,
                "search_aliases": [
                    workflow_name.lower(),
                    workflow_name.lower().replace(" ", "_"),
                    f"{normalized_template_type}_workflow",
                    f"{workflow_name.lower()}_{normalized_template_type}"
                ],
                "creation_context": f"Created from '{normalized_template_type}' template",
                "states_created": result.get("states_created", len(states)),
                "actions_created": result.get("actions_created", len(actions))
            }

            # Enhanced success message with discovery hints
            result["message"] = (
                f"Successfully created '{workflow_name}' workflow using the '{normalized_template_type}' template. "
                f"This workflow includes {len(states)} states and {len(actions)} actions. "
                f"You can find this workflow by searching for '{workflow_name}' or '{normalized_template_type}' workflows."
            )

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
                "error": "At least one field (name or description) must be provided"
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

        return {
            "success": True,
            "workflow_id": workflow_id,
            "updated_name": name,
            "message": f"Successfully updated workflow structure",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update workflow structure: {str(e)}",
            "workflow_id": workflow_id
        }


@server.tool()
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
                "error": "Either states or action_descriptions must be provided"
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

        return {
            "success": True,
            "workflow_id": workflow_id,
            "states_updated": len(update_data.get("states", [])),
            "actions_updated": len(update_data.get("actions", [])),
            "permissions_updated": len(update_data.get("permissions", [])),
            "message": f"Successfully modified workflow flow",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to modify workflow flow: {str(e)}",
            "workflow_id": workflow_id
        }


@server.tool()
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
                "error": "Permission updates list cannot be empty"
            }

        # Validate permission structure
        for perm in permission_updates:
            if "slug" not in perm:
                return {
                    "success": False,
                    "error": "Each permission must have a 'slug' field"
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

        return {
            "success": True,
            "workflow_id": workflow_id,
            "permissions_updated": len(workflow_permissions),
            "permission_slugs": [p["slug"] for p in workflow_permissions],
            "message": f"Successfully updated {len(workflow_permissions)} permissions",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update workflow permissions: {str(e)}",
            "workflow_id": workflow_id
        }


@server.tool()
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
                "error": "Form fields list cannot be empty"
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
                "error": f"Action '{action_slug}' not found in workflow"
            }

        # Prepare update data
        update_data = {"actions": updated_actions}

        # Perform partial update
        result = await svc_client.partial_update_workflow(workflow_id, update_data)

        return {
            "success": True,
            "workflow_id": workflow_id,
            "action_slug": action_slug,
            "form_name": form_name,
            "fields_configured": len(form_fields),
            "field_keys": [f["key"] for f in form_fields],
            "message": f"Successfully configured form '{form_name}' for action '{action_slug}'",
            "validation": result.get("validation", {}),
            "affected_components": result.get("affected_components", []),
            "auto_fixes_applied": result.get("auto_fixes_applied", [])
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to configure workflow form: {str(e)}",
            "workflow_id": workflow_id,
            "action_slug": action_slug
        }


@server.tool()
async def find_workflow_by_any_means(
    search_term: str,
    conversation_context: Optional[str] = None,
    include_partial_matches: bool = True
) -> Dict[str, Any]:
    """
    Multi-strategy workflow search that tries various approaches to find workflows.

    This tool implements a comprehensive search strategy that doesn't give up easily,
    using multiple methods to locate workflows based on user intent.

    Args:
        search_term: What the user is looking for (workflow name, template type, etc.)
        conversation_context: Optional context from current conversation
        include_partial_matches: Whether to include fuzzy/partial matches

    Returns:
        Search results with multiple potential matches and search strategies used
    """
    try:
        search_results = {
            "success": False,
            "search_term": search_term,
            "strategies_used": [],
            "exact_matches": [],
            "partial_matches": [],
            "template_matches": [],
            "recent_matches": [],
            "suggestions": [],
            "best_match": None
        }

        # Get all workflows for comprehensive searching
        workflows_result = await svc_client.list_workflows()
        all_workflows = workflows_result.get("workflows", [])

        if not all_workflows:
            search_results["suggestions"].append("No workflows found. Would you like to create one?")
            return search_results

        # Strategy 1: Exact name matching
        search_results["strategies_used"].append("exact_name_match")
        for workflow in all_workflows:
            if workflow["name"].lower() == search_term.lower():
                search_results["exact_matches"].append({
                    "spec_id": workflow["spec_id"],
                    "name": workflow["name"],
                    "match_reason": "Exact name match"
                })

        # Strategy 2: Partial name matching (fuzzy search)
        if include_partial_matches:
            search_results["strategies_used"].append("partial_name_match")
            search_lower = search_term.lower().replace("_", " ").replace("-", " ")

            for workflow in all_workflows:
                workflow_name_normalized = workflow["name"].lower().replace("_", " ").replace("-", " ")

                # Check if search term is contained in workflow name or vice versa
                if (search_lower in workflow_name_normalized or
                    workflow_name_normalized in search_lower or
                    any(word in workflow_name_normalized for word in search_lower.split() if len(word) > 2)):

                    search_results["partial_matches"].append({
                        "spec_id": workflow["spec_id"],
                        "name": workflow["name"],
                        "match_reason": f"Partial match: '{search_term}' ~ '{workflow['name']}'"
                    })

        # Strategy 3: Template-based matching
        search_results["strategies_used"].append("template_matching")
        template_keywords = {
            "task": ["task", "work", "assignment", "project"],
            "approval": ["approval", "review", "approve", "authorize"],
            "incident": ["incident", "issue", "problem", "bug"],
            "document": ["document", "file", "content", "paper"],
            "request": ["request", "ticket", "service"]
        }

        search_normalized = search_term.lower()
        for template_type, keywords in template_keywords.items():
            if any(keyword in search_normalized for keyword in keywords):
                for workflow in all_workflows:
                    workflow_name_lower = workflow["name"].lower()
                    if any(keyword in workflow_name_lower for keyword in keywords):
                        search_results["template_matches"].append({
                            "spec_id": workflow["spec_id"],
                            "name": workflow["name"],
                            "match_reason": f"Template match: {template_type}-related workflow"
                        })

        # Strategy 4: Recent workflows (assume newer workflows are more likely to be what user wants)
        search_results["strategies_used"].append("recent_workflows")
        # Sort by version (higher version = more recently updated) or modification time if available
        recent_workflows = sorted(all_workflows, key=lambda w: w.get("version", 0), reverse=True)[:5]
        for workflow in recent_workflows:
            if workflow not in [m["name"] for matches in [search_results["exact_matches"], search_results["partial_matches"]] for m in matches]:
                search_results["recent_matches"].append({
                    "spec_id": workflow["spec_id"],
                    "name": workflow["name"],
                    "match_reason": "Recently modified workflow"
                })

        # Determine best match
        if search_results["exact_matches"]:
            search_results["best_match"] = search_results["exact_matches"][0]
            search_results["success"] = True
        elif search_results["partial_matches"]:
            search_results["best_match"] = search_results["partial_matches"][0]
            search_results["success"] = True
        elif search_results["template_matches"]:
            search_results["best_match"] = search_results["template_matches"][0]
            search_results["success"] = True

        # Generate helpful suggestions
        if search_results["success"]:
            total_matches = (len(search_results["exact_matches"]) +
                           len(search_results["partial_matches"]) +
                           len(search_results["template_matches"]))
            if total_matches > 1:
                search_results["suggestions"].append(f"Found {total_matches} potential matches. Using best match: '{search_results['best_match']['name']}'")
        else:
            search_results["suggestions"].extend([
                f"No workflows found matching '{search_term}'",
                "Available workflows: " + ", ".join([w["name"] for w in all_workflows[:5]]),
                "Would you like me to create a new workflow, or try a different search term?"
            ])

        return search_results

    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "search_term": search_term,
            "strategies_used": ["error_fallback"],
            "suggestions": [
                "There was an error searching for workflows",
                "Please try again or use 'list_workflows' to see available options"
            ]
        }


@server.tool()
async def get_conversation_workflows(
    conversation_id: Optional[str] = None,
    include_recent: bool = True,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Get workflows that might be relevant to the current conversation context.

    This tool helps maintain context continuity by tracking workflows that have
    been created or mentioned in recent conversations.

    Args:
        conversation_id: Optional conversation ID for context
        include_recent: Whether to include recently created workflows
        max_results: Maximum number of workflows to return

    Returns:
        Contextually relevant workflows for the conversation
    """
    try:
        # Get all workflows
        workflows_result = await svc_client.list_workflows()
        all_workflows = workflows_result.get("workflows", [])

        if not all_workflows:
            return {
                "success": True,
                "conversation_id": conversation_id,
                "workflows": [],
                "message": "No workflows available"
            }

        # For now, return recent workflows (sorted by version/modification)
        # In future, this could use conversation_id to track workflows mentioned in specific conversations
        relevant_workflows = sorted(
            all_workflows,
            key=lambda w: (w.get("version", 0), w.get("last_modified", 0)),
            reverse=True
        )[:max_results]

        return {
            "success": True,
            "conversation_id": conversation_id,
            "workflows": [
                {
                    "spec_id": w["spec_id"],
                    "name": w["name"],
                    "version": w.get("version", 1),
                    "states_count": w.get("states_count", 0),
                    "relevance_reason": "Recently created or modified"
                }
                for w in relevant_workflows
            ],
            "total_found": len(relevant_workflows),
            "message": f"Found {len(relevant_workflows)} contextually relevant workflows"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get conversation workflows: {str(e)}",
            "conversation_id": conversation_id,
            "workflows": []
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