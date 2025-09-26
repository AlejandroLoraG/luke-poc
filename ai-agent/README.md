# AI Agent - Workflow Conversation Agent

A conversational AI agent built with Pydantic AI that enables natural language interactions with workflow specifications. The agent understands JSON DSL workflow objects and can help users explore, understand, and modify workflows through conversational interface.

## Overview

This AI Agent serves as an MCP (Model Context Protocol) client that:
- Provides natural conversation about workflow structures
- Interprets complex JSON DSL workflow specifications
- Maintains conversation history (up to 15 exchanges)
- Integrates with MCP server for workflow operations
- Uses Google Gemini 2.5 Flash Lite for AI interactions

## Features

- **Natural Language Processing**: Ask questions like "What is this workflow?", "What can I do from this state?", "Add a new action"
- **Workflow Understanding**: Deep comprehension of workflow JSON DSL including states, actions, permissions, forms, and automations
- **MCP Client Integration**: Communicates with MCP server for workflow operations and validation
- **Conversation Memory**: Maintains context across up to 15 conversation exchanges
- **Type-Safe API**: Built with FastAPI and Pydantic models for robust API interactions

## Prerequisites

- Python 3.10+
- Google API key for Gemini access
- MCP Server running (optional for basic functionality)

## Installation

### 1. Clone and Navigate to Directory
```bash
cd ai-agent
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
Create a `.env` file in the ai-agent directory:
```bash
# AI Agent Configuration
GOOGLE_API_KEY=your-google-api-key-here
AI_AGENT_PORT=8001
AI_MODEL=gemini-2.5-flash-lite

# MCP Client Configuration
MCP_SERVER_URL=http://localhost:8002
MCP_CONNECTION_TIMEOUT=30

# Conversation Management
MAX_CONVERSATION_LENGTH=15

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Note**: The Google API key is already configured in the code, but you can override it using environment variables.

## Running Locally

### 1. Start the AI Agent
```bash
# From the ai-agent directory
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload

# Or alternatively
python src/main.py
```

### 2. Verify the Service
Open your browser and visit:
- **API Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/api/v1/health

## API Usage

### Chat with the Agent
```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is this workflow about?",
    "workflow_spec": {
      "specId": "wf_incidentes",
      "specVersion": 1,
      "tenantId": "luke_123",
      "name": "Gestión de Incidentes",
      "slug": "gestion_incidentes",
      "states": [
        {"slug": "reportado", "name": "Incidente reportado", "type": "initial"},
        {"slug": "en_resolucion", "name": "En resolución", "type": "intermediate"},
        {"slug": "resuelto", "name": "Resuelto", "type": "final"}
      ],
      "actions": [
        {
          "slug": "pasar_a_resolucion",
          "from": "reportado",
          "to": "en_resolucion",
          "requiresForm": false,
          "permission": "pasar_a_resolucion"
        }
      ],
      "permissions": [{"slug": "pasar_a_resolucion"}],
      "automations": []
    }
  }'
```

### Example Conversations

**Understanding Workflow Structure:**
```json
{
  "message": "What is this workflow about?",
  "workflow_spec": { /* workflow JSON */ }
}
```

**Exploring States:**
```json
{
  "message": "What can I do from the reportado state?",
  "workflow_spec": { /* workflow JSON */ }
}
```

**Requesting Changes:**
```json
{
  "message": "I want to add a new state called 'escalated' between reportado and en_resolucion",
  "workflow_spec": { /* workflow JSON */ }
}
```

## Testing

### Run Unit Tests
```bash
# Install test dependencies (already included in requirements.txt)
pytest tests/ -v
```

### Run Specific Test Files
```bash
# Test the agent functionality
pytest tests/test_agent.py -v

# Test the API endpoints
pytest tests/test_api.py -v
```

## Project Structure

```
ai-agent/
├── src/
│   ├── agents/
│   │   └── workflow_conversation_agent.py   # Main conversational agent
│   ├── mcp/
│   │   ├── client.py                        # MCP client implementation
│   │   └── tools.py                         # MCP workflow tools
│   ├── core/
│   │   ├── config.py                        # Configuration settings
│   │   └── conversation_manager.py          # Conversation history management
│   ├── api/
│   │   └── chat_router.py                   # FastAPI routes
│   └── main.py                              # Application entry point
├── tests/                                   # Test suite
├── requirements.txt                         # Python dependencies
├── Dockerfile                               # Container configuration
└── README.md                                # This documentation
```

## Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `GOOGLE_API_KEY` | Set in code | Google API key for Gemini access |
| `AI_AGENT_PORT` | `8001` | Port for the FastAPI server |
| `AI_MODEL` | `gemini-2.5-flash-lite` | Gemini model to use |
| `MCP_SERVER_URL` | `http://localhost:8002` | MCP server connection URL |
| `MCP_CONNECTION_TIMEOUT` | `30` | MCP connection timeout in seconds |
| `MAX_CONVERSATION_LENGTH` | `15` | Maximum conversation history length |
| `ENVIRONMENT` | `development` | Application environment |
| `LOG_LEVEL` | `INFO` | Logging level |

## Docker Usage

### Build the Image
```bash
docker build -t ai-agent .
```

### Run the Container
```bash
docker run -p 8001:8001 \
  -e GOOGLE_API_KEY=your-api-key \
  -e MCP_SERVER_URL=http://host.docker.internal:8002 \
  ai-agent
```

## Troubleshooting

### Common Issues

1. **Google API Key Issues**
   - Ensure your Google API key has access to Gemini models
   - Check the key is correctly set in environment or config

2. **MCP Server Connection Failed**
   - The agent will work without MCP server but with limited functionality
   - Ensure MCP server is running on the configured URL
   - Check firewall and network connectivity

3. **Port Already in Use**
   - Change the port in configuration or kill the process using port 8001
   - Use `lsof -i :8001` to find the process using the port

### Logs and Debugging

- Check application logs for detailed error messages
- Use `LOG_LEVEL=DEBUG` for more verbose logging
- Health endpoint shows MCP server connection status

## Integration with Other Components

This AI Agent is designed to work with:
- **MCP Server**: For workflow operations and validation
- **svc-builder**: Via MCP server for workflow data management
- **Shared Schemas**: Uses common Pydantic models for type safety

## Contributing

When contributing to this component:
1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update this README for any new features or configuration options
4. Ensure type safety with Pydantic models
5. Maintain conversation flow and natural language quality