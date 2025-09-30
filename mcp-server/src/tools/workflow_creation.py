"""
Workflow Creation Tools

This module provides tools for creating new workflows from business descriptions
and templates, enabling users to generate complete workflow specifications
from high-level business requirements.
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

        return create_success_response({
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
        }, "create_workflow_from_description")

    except Exception as e:
        return handle_tool_error(e, "create_workflow_from_description", {"workflow_id": None})


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
        return handle_tool_error(e, "create_workflow_from_template",
                               {"available_templates": list(templates.keys()) if 'templates' in locals() else []})


async def get_workflow_templates() -> Dict[str, Any]:
    """
    Get available workflow templates with descriptions.

    Returns:
        Available workflow templates and their descriptions
    """
    try:
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

        return create_success_response({
            "templates": templates,
            "total_templates": len(templates)
        }, "get_workflow_templates")

    except Exception as e:
        return handle_tool_error(e, "get_workflow_templates")