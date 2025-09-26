# AI Agent Component Plan - Natural Workflow Conversation with MCP Integration

## Overview
An AI agent that serves as an MCP client, enabling natural conversations about workflow specifications while leveraging MCP server tools for workflow operations.

## Core Concept
The AI Agent provides a conversational interface where users can:
- Ask questions about workflow structures ("What is this workflow?", "What can I do?")
- Request modifications ("I want to change this state", "Add a new action")
- Understand workflow capabilities through natural language dialogue
- Have the agent interpret and manipulate JSON DSL workflow objects

## Architecture Design

### Primary Agent Capabilities
1. **Workflow Comprehension**: Deep understanding of JSON DSL structure (states, actions, permissions, automations, forms)
2. **Conversational Interface**: Natural language Q&A about workflows
3. **MCP Client Integration**: Connect to MCP server for workflow operations and data retrieval
4. **Workflow Modification**: Apply changes through conversation using MCP tools
5. **Context Awareness**: Maintain conversation history (maximum 15 prompt exchanges)

### Implementation Structure
```
ai-agent/
├── src/
│   ├── agents/
│   │   └── workflow_conversation_agent.py   # Main conversational agent (MCP client)
│   ├── mcp/
│   │   ├── client.py                        # MCP client implementation
│   │   └── tools.py                         # MCP tool integrations
│   ├── core/
│   │   ├── config.py                        # Settings & MCP config
│   │   └── conversation_manager.py          # 15-prompt history management
│   ├── api/
│   │   └── chat_router.py                   # FastAPI chat endpoint
│   └── main.py                              # FastAPI app entry point
├── tests/
│   ├── test_mcp_integration.py              # MCP client tests
│   ├── test_agent_conversations.py          # Conversation flow tests
│   └── test_workflow_understanding.py       # JSON DSL comprehension tests
├── requirements.txt
└── Dockerfile
```

## Technical Implementation

### Dependencies
```
pydantic-ai-slim[google]==0.0.14
pydantic-ai-slim[mcp]==0.0.14      # MCP client support
fastapi==0.115.4
uvicorn[standard]==0.32.0
python-dotenv==1.0.1
pytest==8.3.3
httpx==0.28.0
```

### Environment Configuration
```bash
# AI Agent Configuration
GOOGLE_API_KEY=your-google-gemini-api-key-here
AI_AGENT_PORT=8001
AI_MODEL=gemini-2.5-flash-lite

# MCP Client Configuration
MCP_SERVER_URL=http://localhost:8002
MCP_CONNECTION_TIMEOUT=30

# Conversation Management
MAX_CONVERSATION_LENGTH=15
```

## Key Features

### 1. Workflow Understanding Agent
- **Model**: Gemini 2.5 Flash Lite
- **System Instructions**: Deep knowledge of workflow JSON DSL format
- **Context Injection**: Current workflow specification + conversation history
- **Output**: Natural language responses about workflow structure and capabilities
- **MCP Integration**: Uses MCP tools for workflow operations

### 2. MCP Client Integration
- **Connection Management**: Establish and maintain connection to MCP server
- **Tool Discovery**: Automatically discover available MCP server tools
- **Tool Usage**: Leverage MCP server tools for:
  - Getting workflow specifications
  - Validating state transitions
  - Applying workflow modifications
  - Checking permissions
- **Type Safety**: Use shared Pydantic models for MCP communication

### 3. Conversation Management
- **History Limit**: Maximum 15 prompt-response pairs
- **Context Window**: Rolling conversation with workflow spec always included
- **State Management**: Track current workflow being discussed
- **Session Persistence**: Maintain conversation state across API calls

### 4. Natural Interaction Examples
```
User: "What is this workflow about?"
Agent: "This is a 'Gestión de Incidentes' workflow for managing incidents. It has 3 states: incidents start as 'reportado', can move to 'en_resolucion', and finally to 'resuelto'."

User: "What actions can I take from the reportado state?"
Agent: "From 'reportado' state, you can use the 'pasar_a_resolucion' action to move the incident to 'en_resolucion' state. This doesn't require a form, just the 'pasar_a_resolucion' permission."

User: "I want to add a new state called 'escalated' between reportado and en_resolucion"
Agent: "I understand you want to add an 'escalated' state. Let me use the MCP server to apply these changes: 1) Adding the new state definition, 2) Modifying the 'pasar_a_resolucion' action to go to 'escalated' instead, 3) Creating a new action from 'escalated' to 'en_resolucion'. Should I proceed?"
```

## API Design

### Chat Endpoint
```python
# POST /chat
{
  "message": "What can I do from the reportado state?",
  "workflow_spec": { /* full workflow JSON */ },
  "conversation_id": "conv_123"  # optional for session management
}

# Response
{
  "response": "From the 'reportado' state, you can...",
  "conversation_id": "conv_123",
  "prompt_count": 3,  # out of 15
  "mcp_tools_used": ["get_workflow_states", "check_permissions"]
}

# GET /health
{
  "status": "healthy",
  "mcp_server_connected": true,
  "available_tools": ["get_workflow", "validate_transition", "apply_changes"]
}
```

## Component Integration

### AI Agent ↔ MCP Server Communication
- **Protocol**: Model Context Protocol (MCP)
- **Connection**: HTTP-based MCP client connection
- **Tool Usage**: Agent uses MCP server tools for workflow operations
- **Data Flow**: Agent receives workflow questions → Uses MCP tools for data/operations → Provides natural language responses

### MCP Server ↔ svc-builder Communication
- **Protocol**: HTTP API calls
- **Purpose**: MCP server acts as intermediary between AI Agent and svc-builder
- **Operations**: Workflow CRUD, validation, state management

## Testing Strategy

### Unit Tests
- **Agent Logic**: Test conversation flows using `TestModel`
- **MCP Integration**: Mock MCP server responses
- **Workflow Understanding**: Validate JSON DSL interpretation

### Integration Tests
- **End-to-End**: Full conversation flow with real MCP server
- **Tool Usage**: Verify MCP tool calls work correctly
- **Error Handling**: Test connection failures and recovery

## Implementation Priorities

1. **Phase 1**: Basic conversational agent with workflow understanding
2. **Phase 2**: MCP client integration and tool usage
3. **Phase 3**: Conversation history management
4. **Phase 4**: Workflow modification capabilities
5. **Phase 5**: Testing and error handling

## Success Criteria

The AI Agent component is successful when:
- Users can have natural conversations about workflow structures
- Agent correctly interprets and explains JSON DSL workflow objects
- MCP client successfully connects and uses server tools
- Conversation history is properly managed (15 exchanges max)
- Workflow modifications can be requested and applied through conversation
- All components integrate seamlessly with shared Pydantic models