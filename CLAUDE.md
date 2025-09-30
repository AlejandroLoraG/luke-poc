# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chat Agent PoC is a conversational AI workflow management system that allows users to create and manage business workflows through natural language conversations. The system converts business language into technical workflow specifications using a JSON DSL.

## Commands

### Development and Testing
```bash
# Start all services
docker-compose up --build

# Start services in background
docker-compose up -d --build

# Stop all services
docker-compose down

# View service logs
docker-compose logs ai-agent
docker-compose logs mcp-server
docker-compose logs svc-builder

# Check service status
docker-compose ps

# Health checks
curl http://localhost:8000/api/v1/health  # svc-builder
curl http://localhost:8001/api/v1/health  # AI Agent
```

### Testing
```bash
# Interactive test menu
./run_tests.sh

# Run all conversation tests (both personas)
./test_conversations.sh all

# Run specific persona tests
./test_conversations.sh manager   # Business manager scenario
./test_conversations.sh novice    # Novice user scenario

# Verify created workflows
./test_conversations.sh verify

# Integration tests
python tests/integration_test.py

# Test streaming endpoint
curl -X POST "http://localhost:8001/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need a workflow for document approval"}' \
  --no-buffer

# Test streaming with HTML interface
open test_streaming.html
```

### Individual Service Development
```bash
# svc-builder (port 8000)
cd svc-builder
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e ../  # Install shared package
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# MCP Server (port 8002)
cd mcp-server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e ../  # Install shared package
python src/server.py

# AI Agent (port 8001)
cd ai-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e ../  # Install shared package
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

## Architecture

### Component Overview
```
User Chat ↔ AI Agent (port 8001) ↔ MCP Server (port 8002) ↔ svc-builder (port 8000) ↔ JSON Files
```

**Key Components:**
1. **AI Agent** - Conversational interface using Pydantic AI with Gemini
2. **MCP Server** - Model Context Protocol bridge with 6 organized tool modules
3. **svc-builder** - JSON DSL file management and CRUD operations
4. **Shared Components** - Centralized schemas, config, logging, and error handling

### Shared Component Architecture
- **Shared Package**: `shared/` module installed as editable package via `pyproject.toml`
- **Pydantic Schemas**: `shared/schemas/` - WorkflowSpec, error responses, chat models
- **Configuration**: `shared/config.py` - BaseServiceSettings, service constants, validation
- **Logging**: `shared/logging_config.py` - Structured JSON logging framework
- **Error Handling**: `shared/schemas/errors.py` - StandardErrorResponse patterns

### Critical Models
- `WorkflowSpec`, `WorkflowState`, `WorkflowAction` - Core workflow structures
- `ChatRequest`, `ChatResponse` - Conversation API contracts
- `StandardErrorResponse` - Unified error handling across services
- Models handle both camelCase (external API) and snake_case (internal Python) via aliases

### Key Design Patterns
- **Business Language First**: AI maintains business terminology, never exposes technical JSON details
- **Auto-Generation**: Technical IDs, slugs, and permissions generated from business descriptions
- **MCP Tool Integration**: AI uses standardized tools via FastMCP for workflow operations
- **Conversation Context**: Maintains chat history and workflow context across interactions

### Recent Code Cleanup Achievements ✨
The codebase has undergone comprehensive modernization:

1. **Modular MCP Server**: Split monolithic 1169-line server into 6 organized tool modules:
   - `core_operations.py` (125 lines) - CRUD, validation, listing
   - `workflow_creation.py` (296 lines) - Template and custom creation
   - `workflow_updates.py` (307 lines) - Structure and permission updates
   - `workflow_discovery.py` (213 lines) - Search and exploration
   - `state_management.py` (183 lines) - State and action management
   - `health_monitoring.py` (35 lines) - System health checks

2. **Proper Package Structure**: Eliminated `sys.path.append()` hacks with `pyproject.toml`

3. **Shared Component Framework**: Centralized configuration, logging, and error handling

4. **Standardized Error Responses**: Consistent error patterns with business-friendly conversion

5. **Structured Logging**: JSON logging framework for observability and debugging

### Service Communication
- **ai-agent** connects to **mcp-server** at `http://mcp-server:8002`
- **mcp-server** connects to **svc-builder** at `http://svc-builder:8000`
- All services communicate via HTTP APIs within Docker network
- Services expose ports to host for testing: 8000, 8001, 8002

## Configuration

### Environment Setup
1. Copy `.env.example` to `.env`
2. Set `GOOGLE_API_KEY` to your Google Gemini API key
3. Other settings have reasonable defaults for development

### Key Environment Variables
- `GOOGLE_API_KEY` - Required for AI functionality
- `AI_MODEL=gemini-2.5-flash-lite` - AI model configuration
- `MAX_CONVERSATION_LENGTH=15` - Chat history limit
- Service ports: `AI_AGENT_PORT=8001`, `MCP_SERVER_PORT=8002`, `SERVICE_PORT=8000`

## Streaming API

### Endpoints
- **Standard Chat**: `POST /api/v1/chat` - Returns complete response
- **Streaming Chat**: `POST /api/v1/chat/stream` - Server-Sent Events stream

### Streaming Response Format
```javascript
// Event types:
data: {"type": "start", "conversation_id": "uuid"}
data: {"type": "chunk", "content": "partial response text"}
data: {"type": "complete", "conversation_id": "uuid", "prompt_count": 1, "mcp_tools_used": [...]}
data: {"type": "error", "error": "error message", "conversation_id": "uuid"}
```

### React Integration Example
```javascript
const response = await fetch('/api/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Create a workflow for me",
    conversation_id: conversationId
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.type === 'chunk') {
        setStreamingContent(data.content);
      }
    }
  }
}
```

## Development Notes

### File Structure
- `shared/` - Pydantic models used across all services
- `ai-agent/` - Conversational AI with Pydantic AI and FastAPI
- `mcp-server/` - FastMCP server with workflow management tools
- `svc-builder/` - Workflow JSON file management with FastAPI
- `storage/` - JSON workflow file storage
- `tests/` - Integration tests

### Testing Strategy
The system includes comprehensive persona-based testing that simulates:
- **Experienced Business Manager**: Clear requirements, multiple workflows
- **Novice User**: Learning-oriented, iterative workflow building
- **Verification**: Ensures workflows are properly created and stored

### Important Patterns
- Always use `PYTHONPATH` when running services locally to resolve shared imports
- Services must start in dependency order: svc-builder → mcp-server → ai-agent
- Conversation testing scripts provide realistic usage examples
- MCP tools abstract workflow operations from AI, enabling clean separation