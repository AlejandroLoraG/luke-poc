"""
Workflow Discovery Tools

This module provides sophisticated tools for finding and discovering workflows
through various search strategies, maintaining conversation context, and
providing intelligent search suggestions.
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
        return handle_tool_error(e, "find_workflow_by_any_means", {
            "search_term": search_term,
            "strategies_used": ["error_fallback"],
            "suggestions": [
                "There was an error searching for workflows",
                "Please try again or use 'list_workflows' to see available options"
            ]
        })


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
            return create_success_response({
                "conversation_id": conversation_id,
                "workflows": [],
                "message": "No workflows available"
            }, "get_conversation_workflows")

        # For now, return recent workflows (sorted by version/modification)
        # In future, this could use conversation_id to track workflows mentioned in specific conversations
        relevant_workflows = sorted(
            all_workflows,
            key=lambda w: (w.get("version", 0), w.get("last_modified", 0)),
            reverse=True
        )[:max_results]

        return create_success_response({
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
        }, "get_conversation_workflows")

    except Exception as e:
        return handle_tool_error(e, "get_conversation_workflows", {
            "conversation_id": conversation_id,
            "workflows": []
        })