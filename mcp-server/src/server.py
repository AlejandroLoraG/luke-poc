"""
MCP Server - Streamlined Main Server File

This is the main FastMCP server that registers all workflow management tools
from organized modules. Each tool is imported from its respective module
and registered with the server.
"""

import asyncio
from mcp.server.fastmcp import FastMCP
from config import settings

# Import all tool functions from organized modules
from tools.core_operations import (
    get_workflow,
    list_workflows,
    delete_workflow,
    validate_workflow
)
from tools.workflow_creation import (
    create_workflow_from_description,
    create_workflow_from_template,
    get_workflow_templates
)
from tools.workflow_updates import (
    update_workflow_structure,
    modify_workflow_flow,
    update_workflow_permissions,
    configure_workflow_forms
)
from tools.workflow_discovery import (
    find_workflow_by_any_means,
    get_conversation_workflows
)
from tools.state_management import (
    get_workflow_states,
    get_workflow_actions,
    add_workflow_state,
    update_workflow_actions
)
from tools.health_monitoring import (
    check_svc_builder_health
)

# Create FastMCP server
server = FastMCP(settings.server_name, host="0.0.0.0", port=settings.mcp_server_port)

# Register Core Operations Tools
server.tool()(get_workflow)
server.tool()(list_workflows)
server.tool()(delete_workflow)
server.tool()(validate_workflow)

# Register Workflow Creation Tools
server.tool()(create_workflow_from_description)
server.tool()(create_workflow_from_template)
server.tool()(get_workflow_templates)

# Register Workflow Update Tools
server.tool()(update_workflow_structure)
server.tool()(modify_workflow_flow)
server.tool()(update_workflow_permissions)
server.tool()(configure_workflow_forms)

# Register Workflow Discovery Tools
server.tool()(find_workflow_by_any_means)
server.tool()(get_conversation_workflows)

# Register State Management Tools
server.tool()(get_workflow_states)
server.tool()(get_workflow_actions)
server.tool()(add_workflow_state)
server.tool()(update_workflow_actions)

# Register Health Monitoring Tools
server.tool()(check_svc_builder_health)

# Server startup and management
if __name__ == "__main__":
    print(f"Starting MCP Server on port {settings.mcp_server_port}")
    print("Registered 18 tools across 6 modules:")
    print("  - Core Operations: 4 tools")
    print("  - Workflow Creation: 3 tools")
    print("  - Workflow Updates: 4 tools")
    print("  - Workflow Discovery: 2 tools")
    print("  - State Management: 4 tools")
    print("  - Health Monitoring: 1 tool")

    # Use FastMCP's built-in HTTP transport (SSE - Server-Sent Events)
    print("Starting FastMCP server with HTTP/SSE transport...")
    server.run(transport="streamable-http")