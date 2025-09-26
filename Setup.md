**Project Setup Request for Complete PoC System: AI Agent, MCP Server & svc-builder**

**Context:**
I am building a Proof-of-Concept (PoC) system comprising three main components: an AI Agent, an MCP Server, and a `svc-builder` microservice. All components will leverage Python with Pydantic for Domain-Specific Language (DSL) definitions and FastAPI for communication. The `svc-builder`'s role is to manage workflow definitions, which are complex, nested JSON objects represented by Pydantic models. This PoC aims for simplicity and a clear initial setup.

**Goal:**
Generate the foundational project structure, configuration files, and initial code for all three components of the PoC system:

1. **AI Agent**: Intelligent workflow decision-making using Pydantic AI framework
2. **MCP Server**: Model Context Protocol server for tool integration and communication
3. **svc-builder**: FastAPI microservice for workflow definition management

The setup should be minimalistic, focusing on establishing working applications with shared Pydantic models, type-safe integrations, and basic configuration, ready for further development discussions.

**Chosen Technologies:**
*   **Language:** Python 3.10+
*   **Web Framework:** FastAPI (for svc-builder and MCP Server)
*   **AI Framework:** Pydantic AI (for AI Agent with type-safe AI interactions)
*   **Data Validation/Modeling:** Pydantic (shared across all components)
*   **Protocol:** Model Context Protocol (MCP) for tool integration
*   **Package Manager:** `pip` with `venv`
*   **Environment Variables:** `python-dotenv` for local development
*   **Testing:** `pytest` with `httpx` for API testing
*   **Containerization:** Docker support for each component

**Requirements for the Output:**

## 1. **Overall Project Structure:**
```
/
├── shared/
│   ├── schemas/           # Shared Pydantic models across all components
│   └── __init__.py
├── ai-agent/
│   ├── src/
│   │   ├── agents/        # Pydantic AI agent definitions
│   │   ├── tools/         # Agent tools and functions
│   │   └── main.py        # AI Agent entry point
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── mcp-server/
│   ├── src/
│   │   ├── server.py      # MCP server implementation
│   │   ├── tools/         # MCP tools implementation
│   │   └── handlers/      # Request handlers
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── svc-builder/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # App initialization/settings
│   │   └── main.py        # FastAPI application entry
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── .env.example
├── docker-compose.yml     # Orchestrate all services
└── README.md             # Setup and usage instructions
```

## 2. **Shared Components:**

### **Shared Pydantic Models (`shared/schemas/`):**
*   **Purpose**: Single source of truth for data models used across all components
*   **Models**: `WorkflowSpec`, `WorkflowState`, `WorkflowAction`, `WorkflowPermission`, `WorkflowAutomation`, and nested models
*   **Type Safety**: Use `Literal` for specific string values, `Field(alias="...")` for Python keywords
*   **Validation**: Basic type validation without complex cross-field validators for PoC simplicity

## 3. **AI Agent Component Requirements:**

### **Requirements:**
*   **Dependencies**: `pydantic-ai`, `pydantic`, `python-dotenv`, `httpx`, `pytest`
*   **Agent Definition (`ai-agent/src/agents/workflow_agent.py`)**:
    *   Create a Pydantic AI agent for workflow decision-making
    *   Use structured outputs with shared Pydantic models
    *   Include dependency injection for context (tenant_id, user_id, etc.)
*   **Tools (`ai-agent/src/tools/`)**:
    *   Implement workflow validation tools
    *   State transition validation functions
    *   Permission checking utilities
*   **Main Entry (`ai-agent/src/main.py`)**:
    *   Initialize the AI agent with configuration
    *   Provide CLI interface for testing agent interactions
*   **Tests (`ai-agent/tests/test_agent.py`)**:
    *   Test agent responses with mock AI calls
    *   Validate structured outputs match expected schemas

## 4. **MCP Server Component Requirements:**

### **Requirements:**
*   **Dependencies**: `fastapi`, `uvicorn`, `pydantic`, `python-dotenv`, `httpx`, `pytest`
*   **MCP Server (`mcp-server/src/server.py`)**:
    *   Implement Model Context Protocol server
    *   Handle tool discovery and execution requests
    *   Integration with AI Agent for workflow operations
*   **Tools Implementation (`mcp-server/src/tools/`)**:
    *   Workflow query tools (get workflow specs, states)
    *   Workflow action tools (state transitions, validations)
    *   Integration tools for svc-builder API calls
*   **Request Handlers (`mcp-server/src/handlers/`)**:
    *   Handle MCP protocol messages
    *   Route requests to appropriate tools
    *   Format responses according to MCP specification
*   **Tests (`mcp-server/tests/test_server.py`)**:
    *   Test MCP protocol compliance
    *   Test tool registration and execution
    *   Integration tests with mock svc-builder

## 5. **svc-builder Component Requirements:**

### **Requirements:**
*   **Dependencies**: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv`, `httpx`, `pytest`
*   **Configuration (`svc-builder/app/core/settings.py`)**:
    *   Pydantic BaseSettings for environment variables
    *   Service port configuration (`SERVICE_PORT=8000`)
*   **FastAPI Application (`svc-builder/app/main.py`)**:
    *   Initialize FastAPI application
    *   Health check endpoint (`GET /health`)
    *   Mount API router for workflow operations
*   **API Router (`svc-builder/app/api/router.py`)**:
    *   `GET /workflows/{spec_id}/{spec_version}` - retrieve workflow specs
    *   `POST /workflows` - create/validate workflow specs
    *   `GET /workflows/{spec_id}/states` - get available states
    *   `POST /workflows/{spec_id}/transitions` - execute state transitions
*   **Tests (`svc-builder/tests/test_api.py`)**:
    *   Test all API endpoints
    *   Validate Pydantic model serialization/deserialization

## 6. **Configuration and Environment:**

### **Environment Variables (`.env.example`)**:
```
# AI Agent Configuration
OPENAI_API_KEY=sk-your-openai-key
AI_AGENT_PORT=8001
AI_MODEL=openai:gpt-4

# MCP Server Configuration
MCP_SERVER_PORT=8002
SVC_BUILDER_URL=http://localhost:8000

# svc-builder Configuration
SERVICE_PORT=8000
ENVIRONMENT=development

# Shared Configuration
LOG_LEVEL=INFO
```

## 7. **Integration and Communication:**

### **Component Interactions:**
*   **AI Agent ↔ MCP Server**: Uses MCP protocol for tool execution
*   **MCP Server ↔ svc-builder**: HTTP API calls for workflow operations
*   **Shared Models**: All components import from `shared.schemas`

### **Docker Compose (`docker-compose.yml`)**:
*   Orchestrate all three services
*   Configure service dependencies and networking
*   Environment variable management
*   Development and production profiles

## 8. **Implementation Constraints:**

*   **Code Quality**: Ensure all generated code is concise, adheres to Python best practices (PEP 8), and provides barebones, runnable applications
*   **PoC Simplicity**: Exclude database interaction, complex business logic, authentication, or advanced features beyond the minimum necessary for component integration
*   **Type Safety**: Leverage Pydantic AI's type safety features and shared Pydantic models across all components
*   **Documentation**: Document setup, changes, and project structure for future reference by Claude Code agents
*   **Testing**: Include basic test coverage for each component to validate core functionality
*   **Containerization**: Provide Docker support for easy development environment setup

## 9. **Success Criteria:**

The PoC setup is successful when:
*   All three components can run independently
*   Shared Pydantic models work across components
*   AI Agent can process workflow decisions using Pydantic AI
*   MCP Server can communicate between AI Agent and svc-builder
*   svc-builder can validate and manage workflow specifications
*   Docker Compose orchestrates the complete system
*   Basic tests pass for all components

**Example Workflow JSON (for Pydantic model definition):**

```json
{
    "specId": "wf_incidentes",
    "specVersion": 1,
    "tenantId": "luke_123",
    "name": "Gestión de Incidentes",
    "slug": "gestion_incidentes",
    "states": [
        {
            "slug": "reportado",
            "name": "Incidente reportado",
            "type": "initial"
        },
        {
            "slug": "en_resolucion",
            "name": "En resolución",
            "type": "intermediate"
        },
        {
            "slug": "resuelto",
            "name": "Resuelto",
            "type": "final"
        }
    ],
    "actions": [
        {
            "slug": "pasar_a_resolucion",
            "from": "reportado",
            "to": "en_resolucion",
            "requiresForm": false,
            "permission": "pasar_a_resolucion"
        },
        {
            "slug": "resolver_incidencia",
            "from": "en_resolucion",
            "to": "resuelto",
            "requiresForm": true,
            "permission": "resolver_incidencia",
            "form": {
                "name": "Resolver incidencia",
                "fields": [
                    {
                        "key": "diagnostico_final",
                        "type": "string",
                        "required": true
                    },
                    {
                        "key": "fecha_resolucion",
                        "type": "date",
                        "required": true
                    }
                ]
            }
        }
    ],
    "permissions": [
        {
            "slug": "pasar_a_resolucion"
        },
        {
            "slug": "resolver_incidencia"
        }
    ],
    "automations": [
        {
            "slug": "notify_twilio_on_resuelto",
            "on": {
                "event": "task.state.changed",
                "to": "resuelto"
            },
            "effect": {
                "type": "twilio.notify.subscribers",
                "params": {
                    "template": "resuelto_tpl_v1"
                }
            }
        }
    ]
}
```