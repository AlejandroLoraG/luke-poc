# Context Management Architecture

## Overview

The AI Agent service manages multiple types of context to enable natural, stateful conversations about workflows. This document describes the architecture, components, data flow, and design principles.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Router                          │
│                    (ai-agent/src/api/chat_router.py)           │
└────────────┬────────────────────────────────────────┬──────────┘
             │                                         │
             ▼                                         ▼
┌────────────────────────┐              ┌──────────────────────────┐
│  ConversationManager   │              │   WorkflowMemory         │
│  (with caching +       │              │   (structured memory)    │
│   persistence)         │              │                          │
└────────────────────────┘              └──────────────────────────┘
             │                                         │
             │                                         │
             ▼                                         ▼
┌────────────────────────────────────────────────────────────────┐
│                    WorkflowContext                              │
│                  (@dataclass - Pydantic AI)                    │
└────────────┬────────────────────────────────────────┬──────────┘
             │                                         │
             ▼                                         ▼
┌────────────────────────┐              ┌──────────────────────────┐
│  SystemPrompts         │              │  Pydantic AI Agent       │
│  (modular, adaptive)   │              │  + MCP Tools             │
└────────────────────────┘              └──────────────────────────┘
             │                                         │
             └─────────────┬───────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  AI Response    │
                  └─────────────────┘
```

## Component Responsibilities

### 1. WorkflowContext (Pydantic AI Dependencies)
**File**: `ai-agent/src/agents/workflow_conversation_agent.py`

**Purpose**: Type-safe dependency injection container for agent context

**Structure**:
```python
@dataclass
class WorkflowContext:
    conversation_id: str                    # Current conversation
    turn_count: int                         # Message count
    workflow_spec: Optional[Dict]           # Current workflow (if any)
    conversation_workflows: List[Dict]      # Recent workflows in conversation
    tenant_id: str                          # For multi-tenancy (future)
```

**Responsibilities**:
- Carries conversation metadata (not full history)
- Provides current workflow spec
- Lists recent workflows from structured memory
- Type-safe interface for agent and tools

**Pattern**: Follows Pydantic AI `@dataclass` dependency injection pattern

---

### 2. ConversationManager (History & Caching)
**File**: `ai-agent/src/core/conversation_manager.py`

**Purpose**: Manage conversation history with performance optimizations

**Key Features**:
- **Sliding Window**: Maintains last N turns (default 15)
- **Context Caching**: TTL-based cache for context strings (5min default)
- **Persistence**: Auto-save to disk with atomic writes
- **Summarization**: Progressive LLM-based summarization at 70% threshold

**Responsibilities**:
- Store conversation turns (user message + agent response + tools used)
- Build formatted context strings (cached)
- Persist conversations to disk
- Trigger summarization when nearing max length
- Provide cache statistics

**Performance**:
- Cache hit rate: 90%+
- 50-70% improvement vs uncached
- <200% persistence overhead

---

### 3. ConversationPersistence (Storage)
**File**: `ai-agent/src/core/conversation_persistence.py`

**Purpose**: File-based conversation storage with atomic writes

**Storage Format**: JSON (one file per conversation)

**Key Features**:
- Atomic writes (temp file + rename)
- Auto-load on startup
- Graceful error handling (logs but doesn't crash)

**File Structure**:
```json
{
  "conversation_id": "conv-123",
  "created_at": "2025-01-30T10:00:00",
  "last_updated": "2025-01-30T10:15:00",
  "turn_count": 5,
  "metadata": {},
  "turns": [
    {
      "user_message": "Create a workflow",
      "agent_response": "I'll create that for you...",
      "timestamp": "2025-01-30T10:00:00",
      "mcp_tools_used": ["create_workflow_from_description"]
    }
  ]
}
```

**Migration Path**: Easy to replace with Redis/PostgreSQL (interface remains same)

---

### 4. WorkflowMemory (Structured Memory)
**File**: `ai-agent/src/core/workflow_memory.py`

**Purpose**: Track workflow-conversation relationships outside context window

**Pattern**: Anthropic's "structured note-taking" for persistent memory

**Structure**:
```python
@dataclass
class WorkflowReference:
    spec_id: str              # Workflow ID
    name: str                 # Business-friendly name
    mentioned_at: datetime    # When referenced
    action: str               # "created", "modified", "discussed"
    aliases: List[str]        # Searchable variations
```

**Key Features**:
- **Lightweight**: Stores references, not full specs (~100 bytes each)
- **Bidirectional Indexing**:
  - conversation_id → List[WorkflowReference]
  - workflow_id → Set[conversation_id]
- **Alias Generation**: "Task Management" → ["task management", "my task", "task management workflow", etc.]
- **Context-Aware Search**: Find workflows within a conversation

**Enables**: Natural references like "update my task workflow"

---

### 5. SystemPrompts (Modular Prompts)
**File**: `ai-agent/src/agents/prompts.py`

**Purpose**: Adaptive system prompts sized for specific tasks

**Modes**:
```python
class PromptMode(Enum):
    GENERAL = "general"          # ~400 tokens
    CREATION = "creation"        # ~700 tokens
    SEARCH = "search"            # ~650 tokens
    MODIFICATION = "modification" # ~600 tokens
    ANALYSIS = "analysis"        # ~550 tokens
```

**Composition**:
- Core Identity (always included, ~100 tokens)
- Mode-specific guidance (~300-500 tokens)
- Common tools reference (~200 tokens)
- Error handling guidance (~150 tokens)

**Mode Inference**:
- Analyzes user message keywords
- Considers previous tool usage
- Defaults to GENERAL mode

**Token Savings**: 40-60% vs monolithic 2000-token prompt

---

### 6. ConversationSummarizer (Semantic Compression)
**File**: `ai-agent/src/core/conversation_summarizer.py`

**Purpose**: LLM-based semantic summarization to preserve context

**Strategy**: Progressive summarization at 70% threshold

**Trigger**: When conversation reaches 10-11 turns (70% of max 15)

**Approach**:
1. Take oldest 40% of turns (4-5 turns)
2. Summarize using LLM into compact summary
3. Keep recent 60% as-is
4. Store summary separately
5. Include both in prompt: "[Summary]... [Recent turns]..."

**Fallback**: If summarization fails, fallback to truncation

**Cost**: ~$0.001 per summarization, only at threshold

---

### 7. Context Window Telemetry
**File**: `ai-agent/src/core/telemetry.py`

**Purpose**: Track token usage and context window pressure

**Metrics Tracked**:
- System prompt tokens
- Conversation history tokens
- Workflow spec tokens
- Total context usage
- Percentage of max window

**Token Counting**: Approximation (4 chars ≈ 1 token)

**Warnings**: Alert at >80% of context window

**Exposed Via**: `/api/v1/health` and response metadata

---

## Data Flow

### Request Lifecycle

```
1. User sends message to /api/v1/chat
   ├─ conversation_id (existing or new)
   ├─ message text
   └─ optional workflow_id

2. Router fetches context
   ├─ ConversationManager.get_context_string(conversation_id)
   │  └─ Check cache → hit? return cached : rebuild & cache
   ├─ WorkflowMemory.get_conversation_workflows(conversation_id, limit=5)
   │  └─ Returns recent workflow references
   └─ Build user_context dict

3. Create WorkflowContext
   ├─ conversation_id
   ├─ turn_count
   ├─ workflow_spec (if provided)
   └─ conversation_workflows (from memory)

4. Agent infers prompt mode
   ├─ Analyze message keywords
   ├─ Check previous tools used
   └─ Select appropriate mode (GENERAL, CREATION, etc.)

5. Agent composes system prompt
   ├─ Load CORE_IDENTITY
   ├─ Add mode-specific guidance
   ├─ Include tools reference
   └─ Add error handling

6. Run Pydantic AI agent
   ├─ full_prompt = [summary?] + history + message + workflow_context
   ├─ context_window_telemetry.measure(full_prompt)
   ├─ agent.run(prompt, deps=WorkflowContext)
   └─ Returns (response_text, tools_used)

7. Track workflow operations
   └─ If workflow created/modified → WorkflowMemory.track_workflow()

8. Store conversation turn
   ├─ ConversationManager.add_turn()
   │  ├─ Append to memory
   │  ├─ Check if > max_length → trigger summarization?
   │  ├─ Invalidate cache
   │  └─ Persist to disk (if auto_save)
   └─ Return response to user
```

---

## Configuration

### Environment Variables

```bash
# Conversation Management
MAX_CONVERSATION_LENGTH=15
CONVERSATION_PERSISTENCE_ENABLED=true
CONVERSATION_STORAGE_DIR=./storage/conversations
CONVERSATION_AUTO_SAVE=true

# Caching
CONTEXT_CACHE_TTL=300  # 5 minutes

# Summarization
SUMMARIZATION_ENABLED=true
SUMMARIZATION_THRESHOLD=0.70  # 70% of max_length

# Telemetry
TELEMETRY_ENABLED=true
CONTEXT_WINDOW_WARNING_THRESHOLD=0.80  # Warn at 80%
```

### Programmatic Configuration

```python
from src.core.conversation_manager import ConversationManager

manager = ConversationManager(
    max_length=15,
    cache_ttl=300.0,
    persistence_enabled=True,
    storage_dir="./storage/conversations",
    auto_save=True
)
```

---

## API Endpoints

### Conversation Management
- `POST /api/v1/chat` - Send message (standard response)
- `POST /api/v1/chat/stream` - Send message (streaming SSE)
- `GET /api/v1/conversations` - List all conversations
- `GET /api/v1/conversations/{id}/history` - Get conversation history
- `DELETE /api/v1/conversations/{id}` - Clear from memory
- `DELETE /api/v1/conversations/{id}/permanent` - Delete from disk

### Workflow Memory
- `GET /api/v1/conversations/{id}/workflows` - Workflows in conversation
- `GET /api/v1/workflows/{spec_id}/conversations` - Conversations about workflow

### Monitoring
- `GET /api/v1/health` - Health check with context stats
- `GET /api/v1/memory/stats` - Memory and cache statistics
- `GET /api/v1/debug/prompt-info` - Current prompt mode and token usage

---

## Performance Characteristics

### Caching Layer
- **Cache Hit Rate**: 90%+ in typical usage
- **Performance Improvement**: 50-70% for repeated context fetches
- **TTL**: 5 minutes (configurable)
- **Memory Overhead**: ~1KB per cached conversation

### Persistence Layer
- **Write Time**: 10-50ms per conversation (depends on size)
- **Overhead**: <200% vs in-memory only
- **Storage**: ~5-10KB per conversation (15 turns)
- **Atomic**: No partial writes (temp file + rename)

### Workflow Memory
- **Search Time**: <1ms for 100-item conversation
- **Memory Overhead**: ~100 bytes per workflow reference
- **Scalability**: Linear O(n) with workflow count

### Prompt Optimization
- **Token Reduction**: 40-60% vs monolithic prompt
- **Modes**: 400-700 tokens (vs 2000 monolithic)
- **Mode Switching**: <1ms overhead

### Summarization
- **Trigger**: 70% threshold (10-11 turns of max 15)
- **Latency**: 500-1000ms per summarization
- **Cost**: ~$0.001 per summarization
- **Frequency**: Once per conversation approaching limit

---

## Design Principles

### 1. PoC-Appropriate Simplicity
- File-based storage (not distributed DB)
- Token approximation (not exact)
- Single-tenant (not multi-tenant isolation)
- Simple caching (not Redis)

**Why**: Faster development, easier debugging, good enough for PoC

### 2. Production-Ready Patterns
- Type safety with dataclasses
- Atomic file writes
- Graceful error handling
- Comprehensive logging
- Observability built-in

**Why**: Easy to evolve from PoC to production

### 3. Clear Separation of Concerns
- WorkflowContext: Dependency injection
- ConversationManager: History + caching
- WorkflowMemory: Structured notes
- SystemPrompts: Prompt composition
- ConversationPersistence: Storage layer

**Why**: Each component has single responsibility, easy to test and modify

### 4. Follow Industry Best Practices
- Pydantic AI: `@dataclass` dependency injection
- Anthropic: Structured memory, token optimization
- MCP: Stateless server, stateful client

**Why**: Proven patterns, well-documented, community support

---

## Migration Paths

### Easy Upgrades

**Files → Redis**:
```python
# Change implementation, interface stays same
class RedisPersistence(ConversationPersistence):
    def save_conversation(self, ...): ...
    def load_conversation(self, ...): ...
```

**Single Instance → Distributed**:
- Add session affinity or shared Redis
- No code changes needed

**Token Approximation → Exact**:
```python
# Plug in model-specific tokenizer
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b")
```

**Single Tenant → Multi-Tenant**:
- Add tenant_id isolation in persistence
- Filter queries by tenant_id
- Already structured in WorkflowContext

---

## Testing Strategy

### Unit Tests
- WorkflowContext dataclass behavior
- Cache hit/miss logic
- Persistence atomic writes
- Workflow memory search
- Prompt mode inference

### Integration Tests
- Full request lifecycle
- Context survives restart
- Workflow memory search within conversation
- Summarization triggers correctly

### Performance Tests
- Cache performance improvement
- Persistence overhead measurement
- Workflow memory search speed
- Token savings from modular prompts

### Benchmark Targets
- Cache hit rate: >80%
- Performance improvement: >50%
- Token savings: >40%
- Persistence overhead: <200%

---

## References

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [ADR-001: Context Management](./ADR-001-context-management.md)