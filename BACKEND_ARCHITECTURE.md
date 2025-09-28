# Backend Architecture Documentation

This document provides comprehensive technical documentation for the Chat Agent backend system, designed for developers building frontend applications that communicate with this AI-powered workflow management platform.

## 🏗️ System Architecture Overview

### **High-Level Architecture**
```
Frontend App ↔ AI Agent (8001) ↔ MCP Server (8002) ↔ svc-builder (8000) ↔ JSON Storage
```

### **Service Responsibilities**

**AI Agent (Port 8001)**
- FastAPI application serving chat endpoints
- Pydantic AI integration with Google Gemini
- Conversation management and history
- Business language processing
- Streaming response coordination

**MCP Server (Port 8002)**
- Model Context Protocol server using FastMCP
- Tool orchestration for workflow operations
- Bridge between AI Agent and svc-builder
- 14 specialized workflow management tools

**svc-builder (Port 8000)**
- Workflow JSON DSL management
- File-based storage operations
- CRUD operations for workflow specifications
- Validation and metadata management

## 🤖 AI Agent Service (Port 8001)

### **Core Components**

**FastAPI Application Structure**
```
ai-agent/src/
├── main.py                    # FastAPI app initialization
├── api/
│   ├── chat_router.py         # Chat endpoints (standard + streaming)
│   └── workflow_router.py     # Workflow management endpoints
├── agents/
│   └── workflow_conversation_agent.py  # Pydantic AI agent implementation
├── core/
│   ├── config.py              # Settings and configuration
│   ├── conversation_manager.py # In-memory conversation history
│   └── workflow_storage.py    # In-memory workflow cache
└── data/
    └── sample_workflows.py    # Pre-loaded sample workflows
```

### **Conversation Management**

**ConversationManager Class**
- Maintains conversation history in memory
- Configurable max length (default: 15 turns)
- Automatic conversation trimming
- Context string generation for AI prompts

**ConversationTurn Data Structure**
```python
@dataclass
class ConversationTurn:
    user_message: str
    agent_response: str
    timestamp: datetime
    mcp_tools_used: List[str]
```

### **AI Agent Implementation**

**WorkflowConversationAgent Class**
- Pydantic AI Agent with Google Gemini integration
- MCP server connection for tool access
- Business consultant persona with detailed instructions
- Streaming and non-streaming response modes

**Agent Configuration**
- Model: `gemini-2.5-flash-lite` (configurable)
- Instructions: 139-line business consultant persona
- Tools: Connected via MCP server at runtime
- Context: Workflow specifications and conversation history

**Key Methods**
- `chat()` - Standard request-response pattern
- `chat_stream()` - Real-time streaming responses using `Agent.run_stream()`

### **Chat Endpoints**

**Standard Chat: `POST /api/v1/chat`**
```python
# Request
{
    "message": str,
    "conversation_id": Optional[str],
    "workflow_id": Optional[str],
    "workflow_spec": Optional[WorkflowSpec]
}

# Response
{
    "response": str,
    "conversation_id": str,
    "prompt_count": int,
    "mcp_tools_used": List[str],
    "workflow_source": Optional[str]
}
```

**Streaming Chat: `POST /api/v1/chat/stream`**
- Returns Server-Sent Events (SSE)
- Content-Type: `text/event-stream`
- CORS enabled for frontend integration
- Real-time chunk delivery via `Agent.run_stream()`

**SSE Event Format**
```
data: {"type": "start", "conversation_id": "uuid"}
data: {"type": "chunk", "content": "partial text"}
data: {"type": "complete", "conversation_id": "uuid", "prompt_count": 1, "mcp_tools_used": [...]}
data: {"type": "error", "error": "error message"}
```

### **Workflow Context Integration**

**Priority System**
1. `workflow_spec` (full specification object)
2. `workflow_id` (loads from storage)
3. None (general conversation)

**Context Enhancement**
- Workflow summary added to AI prompt
- Previous conversation history included
- User context object for future extensibility

## 🌉 MCP Server (Port 8002)

### **FastMCP Server Implementation**

**Server Configuration**
- Transport: `streamable-http` (HTTP with SSE support)
- Connection: HTTP client to svc-builder
- Tools: 14 workflow management functions

**Connection Architecture**
```
AI Agent → HTTP/SSE → MCP Server → HTTP → svc-builder
```

### **Available MCP Tools**

**Workflow Retrieval**
- `get_workflow(spec_id)` - Retrieve workflow by ID
- `list_workflows()` - List all available workflows
- `get_workflow_states(spec_id)` - Get workflow states
- `get_workflow_actions(spec_id)` - Get workflow actions

**Workflow Management**
- `create_workflow_from_description(name, description, states, actions)` - Business-friendly creation
- `create_workflow_from_template(workflow_name, template_type, customizations)` - Template-based creation
- `add_workflow_state(workflow_id, state_name, position)` - Add states dynamically
- `update_workflow_actions(workflow_id, action_descriptions)` - Update actions

**Templates and Validation**
- `get_workflow_templates()` - Available templates
- `validate_workflow(spec_id)` - Validate workflow structure
- `delete_workflow(spec_id)` - Remove workflows

**System Health**
- `check_svc_builder_health()` - Service connectivity status

### **Business Logic Layer**

**Auto-Generation Features**
- Workflow IDs: `"approval process"` → `"wf_approval"`
- State slugs: `"Under Review"` → `"under_review"`
- Action slugs: `"Submit for approval"` → `"submit_for_approval"`
- Permission slugs: Auto-generated with `_perm` suffix
- State types: Auto-assigned (`initial`, `intermediate`, `final`)

**Template System**
Available templates: `approval`, `incident`, `task`, `document_review`, `request_handling`

Each template includes:
- Predefined states and actions
- Business descriptions
- Use case examples
- Customization options

**Error Handling Strategy**
- Never expose technical errors to AI
- Graceful fallbacks for failed operations
- Business-friendly error messages
- Automatic retry logic for transient failures

## 📁 svc-builder Service (Port 8000)

### **FastAPI Application Structure**
```
svc-builder/app/
├── main.py                    # FastAPI app with lifecycle management
├── api/
│   └── router.py              # Workflow CRUD endpoints
└── core/
    ├── settings.py            # Configuration
    ├── file_manager.py        # JSON file operations
    └── sample_loader.py       # Sample workflow initialization
```

### **Storage Implementation**

**File-Based Storage**
- Location: `/app/storage/workflows/`
- Format: JSON files named by `spec_id`
- Atomic operations for consistency
- Metadata tracking (creation, modification times)

**Sample Workflow Initialization**
- 3 pre-loaded workflows on startup
- `wf_incidentes` - Incident Management
- `wf_approval` - Document Approval
- `wf_tasks` - Task Management

### **Workflow CRUD API**

**Core Endpoints**
```
GET    /api/v1/workflows           # List all workflows
GET    /api/v1/workflows/{spec_id} # Get specific workflow
POST   /api/v1/workflows           # Create new workflow
PUT    /api/v1/workflows/{spec_id} # Update workflow
DELETE /api/v1/workflows/{spec_id} # Delete workflow
```

**Extended Operations**
```
POST   /api/v1/workflows/{spec_id}/validate    # Validate workflow
POST   /api/v1/workflows/{spec_id}/duplicate   # Duplicate workflow
DELETE /api/v1/workflows                       # Clear all workflows
```

**Response Format**
```python
# List Response
{
    "workflows": [
        {
            "spec_id": str,
            "name": str,
            "slug": str,
            "tenant_id": str,
            "version": int,
            "states_count": int,
            "actions_count": int,
            "file_size": int,
            "last_modified": float
        }
    ],
    "total_count": int,
    "storage_stats": {
        "total_workflows": int,
        "storage_path": str,
        "total_size_bytes": int,
        "workflow_ids": List[str]
    }
}
```

## 📊 Data Models (Shared Schema)

### **Core Workflow Models**

**WorkflowSpec** (Primary Model)
```python
class WorkflowSpec(BaseModel):
    spec_id: str = Field(alias="specId")
    spec_version: int = Field(alias="specVersion", default=1)
    tenant_id: str = Field(alias="tenantId", default="luke_123")
    name: str
    slug: str
    states: List[WorkflowState] = Field(default_factory=list)
    actions: List[WorkflowAction] = Field(default_factory=list)
    permissions: List[WorkflowPermission] = Field(default_factory=list)
    automations: List[WorkflowAutomation] = Field(default_factory=list)
```

**WorkflowState**
```python
class WorkflowState(BaseModel):
    slug: str
    name: str
    type: StateType  # "initial", "intermediate", "final"
```

**WorkflowAction**
```python
class WorkflowAction(BaseModel):
    slug: str
    from_: str = Field(alias="from")
    to: str
    requires_form: bool = Field(alias="requiresForm", default=False)
    permission: str
    form: Optional[WorkflowForm] = None
```

**WorkflowPermission**
```python
class WorkflowPermission(BaseModel):
    slug: str
    description: Optional[str] = None
```

### **Chat Communication Models**

**ChatRequest**
```python
class ChatRequest(BaseModel):
    message: str
    workflow_spec: Optional[WorkflowSpec] = None
    workflow_id: Optional[str] = None
    conversation_id: Optional[str] = None
```

**ChatResponse**
```python
class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    prompt_count: int
    mcp_tools_used: List[str] = []
    workflow_source: Optional[str] = None
```

**StreamingChatChunk**
```python
class StreamingChatChunk(BaseModel):
    type: str  # "start", "chunk", "complete", "error"
    content: Optional[str] = None
    conversation_id: Optional[str] = None
    prompt_count: Optional[int] = None
    mcp_tools_used: Optional[List[str]] = None
    workflow_source: Optional[str] = None
    error: Optional[str] = None
```

### **Field Aliasing System**

**Pydantic Configuration**
- External API: camelCase (`specId`, `tenantId`, `requiresForm`)
- Internal Python: snake_case (`spec_id`, `tenant_id`, `requires_form`)
- Automatic conversion via `Field(alias="...")` and `populate_by_name = True`

## 🔧 Configuration Management

### **Environment Variables**

**AI Agent Configuration**
```bash
GOOGLE_API_KEY=required              # Google Gemini API key
AI_AGENT_PORT=8001                   # Service port
AI_MODEL=gemini-2.5-flash-lite       # AI model selection
MCP_SERVER_URL=http://mcp-server:8002 # MCP server connection
MAX_CONVERSATION_LENGTH=15           # Chat history limit
```

**MCP Server Configuration**
```bash
MCP_SERVER_PORT=8002                 # Service port
SVC_BUILDER_URL=http://svc-builder:8000 # svc-builder connection
SVC_BUILDER_TIMEOUT=30               # HTTP timeout
```

**svc-builder Configuration**
```bash
SERVICE_PORT=8000                    # Service port
ENVIRONMENT=development              # Environment mode
LOG_LEVEL=INFO                       # Logging level
```

**Shared Configuration**
```bash
COMPOSE_PROJECT_NAME=chat-agent-poc  # Docker compose project name
```

### **Docker Network Architecture**

**Service Dependencies**
1. `svc-builder` starts first (no dependencies)
2. `mcp-server` starts after `svc-builder` is healthy
3. `ai-agent` starts after `mcp-server` is healthy

**Health Check Configuration**
- All services include health check endpoints
- Docker health checks verify service readiness
- Dependency startup order enforced via `depends_on`

**Internal Network Communication**
- Services communicate via Docker network names
- `ai-agent` → `mcp-server:8002`
- `mcp-server` → `svc-builder:8000`
- External access via port mapping to localhost

## 🚀 Enhanced Streaming Implementation

### **Architecture Overview**

The streaming system follows a clean, layered architecture designed for reliability, performance, and maintainability:

```
FastAPI Router → Streaming Service → Agent Streaming → Pydantic AI
```

### **Streaming Service Layer**

**StreamingService Class (`core/streaming_service.py`)**
- Centralized streaming logic with clean separation of concerns
- Content deduplication using SHA-256 hashing
- Sequence tracking for reliable chunk ordering
- Comprehensive metrics collection and monitoring
- Robust error handling with graceful degradation

**Key Features:**
- **Multi-layer Deduplication**: Prevents duplicate content at both agent and service levels
- **Streaming Metrics**: Real-time monitoring of chunk count, response length, and timing
- **Sequence Management**: Unique sequence IDs for client-side ordering and debugging
- **Clean Architecture**: Separation between streaming logic and HTTP concerns

### **Enhanced Agent Streaming**

**Primary Streaming Method: `stream_text(delta=True)`**
- True incremental text deltas from Pydantic AI
- No cumulative content - only new text portions
- Eliminates duplication at the source
- Optimal for real-time user experience

**Fallback Method: Enhanced `stream_output()`**
- Intelligent incremental content extraction
- Content hash-based deduplication
- Maintains compatibility with different Pydantic AI versions
- Robust error handling for edge cases

**Agent Architecture Improvements:**
```python
# Clean method separation
async def chat_stream()          # Main streaming interface
def _build_contextual_prompt()   # Prompt construction
async def _generate_ai_stream()  # Primary AI streaming
async def _fallback_stream_output() # Compatibility fallback
```

### **Server-Sent Events (SSE) Implementation**

**Enhanced SSE Event Format**
```json
{
  "type": "start|chunk|complete|error",
  "content": "Incremental text content",
  "sequence_id": "stream_1_1234567890",
  "chunk_count": 1,
  "timestamp": 1234567890.123
}
```

**Streaming Event Types:**
- **`start`**: Stream initialization with conversation ID
- **`chunk`**: Incremental content with sequence tracking
- **`complete`**: Stream completion with comprehensive metrics
- **`error`**: Error handling with context preservation

**Enhanced Completion Event:**
```json
{
  "type": "complete",
  "conversation_id": "uuid",
  "prompt_count": 1,
  "mcp_tools_used": ["tool1", "tool2"],
  "workflow_source": "provided_spec",
  "streaming_metrics": {
    "total_chunks": 5,
    "unique_sequences": 5,
    "response_length": 234,
    "duration_ms": 1234.5
  }
}
```

### **Deduplication Strategy**

**Three-Layer Deduplication System:**

1. **Agent Level**: Content hashing prevents duplicate text generation
2. **Service Level**: Sequence tracking ensures unique chunk delivery
3. **Router Level**: SSE-level validation for final safety net

**Content Hashing Algorithm:**
```python
import hashlib
content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
```

**Sequence ID Format:**
```
Primary: "stream_{counter}_{timestamp_ms}"
Fallback: "seq_{counter}_{timestamp_ms}"
Error: "error_{timestamp_ms}"
```

### **Performance Optimizations**

**Streaming Performance Features:**
- **Zero Debouncing**: Eliminates artificial delays (`debounce_by=None`)
- **Incremental Processing**: Only new content is transmitted
- **Efficient Hashing**: Fast MD5 hashing for deduplication
- **Memory Efficient**: Minimal state tracking during streaming

**Monitoring and Metrics:**
- **Real-time Metrics**: Chunk count, response length, duration tracking
- **Comprehensive Logging**: Debug information for troubleshooting
- **Error Tracking**: Detailed error context for diagnostics
- **Performance Monitoring**: Response time and throughput metrics

### **Error Handling and Resilience**

**Robust Error Handling:**
- **Graceful Degradation**: Fallback methods for compatibility
- **Context Preservation**: Conversation state maintained during errors
- **User-Friendly Messages**: Technical errors masked from users
- **Comprehensive Logging**: Detailed error information for debugging

**Error Recovery Mechanisms:**
```python
try:
    # Primary streaming method
    async for delta in result.stream_text(delta=True):
        yield delta
except (AttributeError, TypeError):
    # Automatic fallback to compatibility mode
    yield from fallback_stream_output(result)
```

### **Client Integration Guide**

**JavaScript/TypeScript Example:**
```javascript
const response = await fetch('/api/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: "Create a workflow" })
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

      switch (data.type) {
        case 'start':
          console.log('Stream started:', data.conversation_id);
          break;
        case 'chunk':
          appendToUI(data.content); // Incremental content
          break;
        case 'complete':
          console.log('Stream complete:', data.streaming_metrics);
          break;
        case 'error':
          handleError(data.error);
          break;
      }
    }
  }
}
```

**React Integration Pattern:**
```typescript
const [streamingContent, setStreamingContent] = useState('');
const [isStreaming, setIsStreaming] = useState(false);

// Append incremental content (no replacement needed)
const handleChunk = (data: ChunkEvent) => {
  setStreamingContent(prev => prev + data.content);
};
```

## 🎯 Business Logic Implementation

### **AI Persona and Instructions**

**Business Consultant Persona**
- 139-line system instruction defining AI behavior
- Business language enforcement (no technical terms)
- Natural requirement gathering methodology
- Error masking and graceful degradation

**Key Behavioral Rules**
1. Never mention JSON, schemas, validation, IDs, slugs
2. Use business terms: "process", "workflow", "steps", "stages"
3. Auto-generate all technical fields from business descriptions
4. Provide workflow design guidance and best practices
5. Handle technical errors without exposing them to users

### **Workflow Auto-Generation Logic**

**ID Generation Algorithm**
```python
# Business name to technical ID
name = "Document Approval Process"
spec_id = f"wf_{name.lower().replace(' ', '_').replace('-', '_')}"
# Result: "wf_document_approval_process"
```

**State Type Assignment**
```python
for i, state in enumerate(states):
    if i == 0:
        state_type = "initial"
    elif i == len(states) - 1:
        state_type = "final"
    else:
        state_type = "intermediate"
```

**Permission Generation**
```python
action_slug = action_name.lower().replace(' ', '_').replace('-', '_')
permission_slug = f"{action_slug}_perm"
permission_description = f"Permission to {action_name.lower()}"
```

### **Template System Architecture**

**Template Structure**
```python
templates = {
    "approval": {
        "description": "Standard approval process",
        "states": ["Submitted", "Under Review", "Approved"],
        "actions": ["Submit for Review", "Approve Request"],
        "use_cases": ["Document approval", "Request approval", "Budget approval"]
    }
    # ... more templates
}
```

**Customization Support**
- Override states, actions, or descriptions
- Maintain template structure while allowing modifications
- Business-friendly template selection process

## 🔍 Error Handling and Monitoring

### **Error Handling Strategy**

**AI Agent Level**
- Catch all exceptions from MCP tools
- Convert technical errors to business language
- Graceful degradation when tools unavailable
- Conversation context preservation during errors

**MCP Server Level**
- HTTP client error handling for svc-builder communication
- Tool execution error wrapping
- Health check integration
- Connection retry logic

**svc-builder Level**
- File system operation error handling
- JSON validation and parsing errors
- Atomic operation guarantees
- Rollback capability for failed operations

### **Health Check Implementation**

**Multi-Level Health Checks**
1. Service-specific health endpoints (`/api/v1/health`)
2. Docker health check commands
3. Inter-service connectivity verification
4. Resource availability monitoring

**Health Check Response Format**
```python
{
    "status": "healthy|unhealthy",
    "mcp_server_connected": bool,
    "workflow_storage": {...},
    "test_mode": bool,
    "model": str,
    "error": Optional[str]
}
```

## 🧪 Testing Infrastructure

### **Persona-Based Testing**

**Two Test Personas**
1. **Sarah (Business Manager)** - Experienced, clear requirements, efficient
2. **Mike (Novice User)** - Learning-oriented, iterative, needs guidance

**Test Scripts**
- `./run_tests.sh` - Interactive test menu
- `./test_conversations.sh` - Automated persona conversations
- Conversation verification and workflow creation validation

**Test Coverage**
- Streaming and non-streaming endpoints
- Workflow creation and modification
- Context preservation across conversations
- Tool usage verification
- Error handling scenarios

### **Integration Test Suite**

**Automated Validation**
- Service startup and health verification
- End-to-end conversation flows
- Workflow persistence validation
- MCP tool execution verification
- API response format compliance

## 🔮 Extension Points

### **Adding New MCP Tools**

**Tool Development Pattern**
```python
@server.tool()
async def new_workflow_tool(param: str) -> Dict[str, Any]:
    """
    Tool description for AI agent.

    Args:
        param: Parameter description

    Returns:
        Structured response for AI consumption
    """
    try:
        # Business logic implementation
        result = await some_business_operation(param)
        return {
            "success": True,
            "data": result,
            "message": "Business-friendly success message"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Business-friendly error message"
        }
```

### **Conversation Context Extension**

**User Context Enhancement**
- Authentication information
- User preferences and settings
- Organization context
- Role-based permissions

**Workflow Context Extension**
- Execution state tracking
- Performance metrics
- Usage analytics
- Audit trail integration

### **Storage Backend Extension**

**Database Integration Points**
- Replace file-based storage with database
- Add transaction support
- Implement caching layers
- Support for concurrent access

### **AI Model Extension**

**Multi-Model Support**
- Model selection based on conversation type
- Fallback model configuration
- Performance optimization
- Cost management strategies

## 🎯 Frontend Integration Considerations

### **API Contract Stability**

**Versioned API Endpoints**
- Current version: `/api/v1/`
- Backward compatibility guarantees
- Deprecation policy for breaking changes
- Feature flag support for gradual rollouts

### **Real-Time Communication**

**WebSocket Future Support**
- Current: HTTP + SSE
- Planned: WebSocket for bidirectional communication
- Push notifications for workflow updates
- Real-time collaboration features

### **Authentication Integration Points**

**Future Authentication Support**
- JWT token validation middleware
- Role-based access control
- API key management
- OAuth2 integration points

### **Performance Considerations**

**Scaling Recommendations**
- Horizontal scaling via load balancing
- Database connection pooling
- Redis for conversation state
- CDN for static assets

**Rate Limiting**
- Per-user conversation limits
- API key-based rate limiting
- Model usage quotas
- Graceful degradation strategies

This backend system provides a robust, scalable foundation for AI-powered workflow management with comprehensive tooling for natural language interaction and real-time streaming capabilities.