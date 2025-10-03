# Session Management & Chat-Workflow Binding Features

## Overview

This document describes the new session management and chat-workflow binding features added to the chat-agent system.

## Core Concepts

### 1. Sessions
- **What**: A session groups multiple chats for a user
- **Why**: Organize conversations without requiring authentication
- **Lifetime**: Persists across app restarts (file-based storage)

### 2. Chat Bindings
- **What**: Each chat can be bound to exactly ONE workflow
- **Why**: Prevents confusion when managing multiple workflows
- **Behavior**: After workflow creation, the chat becomes dedicated to that workflow

### 3. Workflow Binding Rules
- ✅ **Allowed**: View, update, manage the bound workflow
- ❌ **Blocked**: Create new workflows in same chat
- 🔄 **Workaround**: Start a new chat in the same session

## API Changes

### New Endpoints

#### Create Session
```bash
POST /api/v1/sessions?user_identifier=my_user
```

**Response:**
```json
{
  "session_id": "sess_abc123def456",
  "created_at": "2025-10-03T00:00:00",
  "last_activity": "2025-10-03T00:00:00",
  "user_identifier": "my_user"
}
```

#### Get Session Details
```bash
GET /api/v1/sessions/{session_id}
```

**Response:**
```json
{
  "session": {
    "session_id": "sess_abc123def456",
    "created_at": "2025-10-03T00:00:00",
    "last_activity": "2025-10-03T00:05:00",
    "user_identifier": "my_user"
  },
  "chats": [
    {
      "conversation_id": "conv_123",
      "session_id": "sess_abc123def456",
      "bound_workflow_id": "wf_approval",
      "is_bound": true,
      "created_at": "2025-10-03T00:01:00",
      "last_activity": "2025-10-03T00:05:00"
    }
  ],
  "total_chats": 1
}
```

#### Get Chat Binding
```bash
GET /api/v1/chats/{conversation_id}/binding
```

**Response:**
```json
{
  "conversation_id": "conv_123",
  "session_id": "sess_abc123def456",
  "bound_workflow_id": "wf_approval",
  "is_bound": true,
  "created_at": "2025-10-03T00:01:00",
  "last_activity": "2025-10-03T00:05:00"
}
```

### Updated Endpoints

#### Chat (Standard)
```bash
POST /api/v1/chat
```

**Request (BREAKING CHANGE):**
```json
{
  "message": "Create an approval workflow",
  "session_id": "sess_abc123def456",  // NOW REQUIRED
  "conversation_id": "conv_123",      // Optional (auto-generated if omitted)
  "language": "en"
}
```

**Response (Enhanced):**
```json
{
  "response": "✅ Done! Your 'Approval Process' workflow is active...",
  "conversation_id": "conv_123",
  "session_id": "sess_abc123def456",           // NEW
  "prompt_count": 1,
  "workflow_created_id": "wf_approval",
  "workflow_bound_id": "wf_approval",          // NEW
  "is_chat_locked": true,                      // NEW
  "workflow_source": "bound_workflow:wf_approval",
  "language": "en",
  "mcp_tools_used": ["create_workflow_from_description"]
}
```

#### Chat (Streaming)
```bash
POST /api/v1/chat/stream
```

Same request/response changes as standard chat endpoint.

## Usage Examples

### Example 1: Creating Multiple Workflows in One Session

```python
import requests

BASE_URL = "http://localhost:8001"

# Step 1: Create session
resp = requests.post(f"{BASE_URL}/api/v1/sessions",
                     params={"user_identifier": "john_doe"})
session = resp.json()
session_id = session["session_id"]

# Step 2: Create first workflow in first chat
resp = requests.post(f"{BASE_URL}/api/v1/chat", json={
    "message": "Create approval workflow: Draft → Review → Approved",
    "session_id": session_id
})
chat1 = resp.json()
print(f"Chat 1: {chat1['conversation_id']}")
print(f"Workflow 1: {chat1['workflow_bound_id']}")
print(f"Is locked: {chat1['is_chat_locked']}")  # True

# Step 3: Try creating another workflow in SAME chat (AI will refuse)
resp = requests.post(f"{BASE_URL}/api/v1/chat", json={
    "message": "Create onboarding workflow: New → Training → Active",
    "session_id": session_id,
    "conversation_id": chat1['conversation_id']  # Same chat!
})
response = resp.json()
print(response['response'])
# Output: "This chat is dedicated to your 'Approval Process' workflow.
#          To create a new workflow, please start a new chat."

# Step 4: Create second workflow in NEW chat (same session)
resp = requests.post(f"{BASE_URL}/api/v1/chat", json={
    "message": "Create onboarding workflow: New → Training → Active",
    "session_id": session_id
    # No conversation_id = new chat
})
chat2 = resp.json()
print(f"Chat 2: {chat2['conversation_id']}")
print(f"Workflow 2: {chat2['workflow_bound_id']}")
print(f"Is locked: {chat2['is_chat_locked']}")  # True

# Step 5: Get session overview
resp = requests.get(f"{BASE_URL}/api/v1/sessions/{session_id}")
session_details = resp.json()
print(f"Total chats in session: {session_details['total_chats']}")  # 2
for chat in session_details['chats']:
    print(f"  - Chat {chat['conversation_id']}: bound to {chat['bound_workflow_id']}")
```

### Example 2: Working with Bound Workflow

```python
# Continue chat with bound workflow
resp = requests.post(f"{BASE_URL}/api/v1/chat", json={
    "message": "Add a 'Rejected' state to the workflow",
    "session_id": session_id,
    "conversation_id": chat1['conversation_id']  # Bound chat
})

# AI will update the bound workflow (wf_approval)
response = resp.json()
print(response['response'])  # "I've added the 'Rejected' state..."
print(response['workflow_bound_id'])  # Still: wf_approval
```

## Data Models

### Session
```python
@dataclass
class Session:
    session_id: str                    # e.g., "sess_abc123"
    created_at: datetime
    last_activity: datetime
    user_identifier: str               # Manual ID or IP
    metadata: Dict[str, Any]           # Extensible metadata
```

### ChatBinding
```python
@dataclass
class ChatBinding:
    conversation_id: str
    session_id: str
    created_at: datetime
    bound_workflow_id: Optional[str]   # None until workflow created
    binding_locked_at: Optional[datetime]
    last_activity: datetime

    def is_bound() -> bool             # True if workflow bound
    def can_create_workflow() -> bool  # False if already bound
    def bind(workflow_id: str)         # Bind to workflow (once)
```

### WorkflowContext (Enhanced)
```python
@dataclass
class WorkflowContext:
    # ... existing fields ...

    # NEW fields
    session_id: Optional[str]
    bound_workflow_id: Optional[str]
    is_workflow_bound: bool

    def can_create_new_workflow() -> bool
```

## Storage

### File Structure
```
storage/
├── sessions/
│   ├── sess_abc123.json
│   └── sess_def456.json
├── chat_bindings/
│   ├── conv_xyz789.json
│   └── conv_123abc.json
└── workflows/
    ├── wf_approval.json
    └── wf_onboarding.json
```

### Session File Format
```json
{
  "session_id": "sess_abc123",
  "created_at": "2025-10-03T00:00:00",
  "last_activity": "2025-10-03T00:05:00",
  "user_identifier": "john_doe",
  "metadata": {}
}
```

### Binding File Format
```json
{
  "conversation_id": "conv_123",
  "session_id": "sess_abc123",
  "created_at": "2025-10-03T00:01:00",
  "bound_workflow_id": "wf_approval",
  "binding_locked_at": "2025-10-03T00:01:30",
  "last_activity": "2025-10-03T00:05:00"
}
```

## AI Behavior

### Binding Enforcement

When a chat is bound to a workflow, the AI receives a dynamic system prompt:

**English:**
```
🔒 IMPORTANT WORKFLOW BINDING CONSTRAINT:

This chat is EXCLUSIVELY bound to workflow: "Approval Process" (ID: wf_approval)

YOU CAN:
✅ View details of this workflow
✅ Update this workflow (states, actions, permissions)
✅ Answer questions about this workflow
✅ Help manage this workflow

YOU CANNOT:
❌ Create new workflows (this chat already has one)
❌ Switch to a different workflow
❌ List or search other workflows

If the user tries to create a new workflow, politely explain:
"This chat is dedicated to your 'Approval Process' workflow.
 To create a new workflow, please start a new chat in your session."
```

**Spanish** (equivalent message in Spanish is also supported)

## Migration Notes

### Breaking Changes
- `ChatRequest.session_id` is now **REQUIRED**
- Clients must create a session before chatting

### Backward Compatibility
- Existing conversations without sessions can be auto-migrated
- Add a migration endpoint if needed: `POST /api/v1/sessions/migrate`

### Migration Strategy
```python
# Option 1: Require session upfront (current approach)
# - Simple and clean
# - Requires frontend update

# Option 2: Auto-create session if missing (future enhancement)
# - Better backward compatibility
# - Requires endpoint update to make session_id optional initially
```

## Testing

### Unit Tests
```bash
python3 test_session_binding_unit.py
```

Tests:
- ✅ Session model creation and updates
- ✅ ChatBinding model with binding logic
- ✅ SessionManager with persistence
- ✅ ChatBindingManager with binding enforcement
- ✅ ConversationTurn enhancements

### Integration Test
```bash
# Requires Docker services running
docker-compose up -d
python3 test_session_feature.py
```

Tests:
- ✅ Full session lifecycle
- ✅ Workflow creation and binding
- ✅ AI enforcement of binding rules
- ✅ Multiple chats in one session

## Best Practices

### Frontend Integration

1. **Session Management**
   ```javascript
   // Create session on app load or user login
   const session = await createSession(userIdentifier);
   localStorage.setItem('session_id', session.session_id);
   ```

2. **Chat Management**
   ```javascript
   // New chat for new workflow
   const newChat = await fetch('/api/v1/chat', {
     method: 'POST',
     body: JSON.stringify({
       message: userMessage,
       session_id: localStorage.getItem('session_id')
       // No conversation_id = new chat
     })
   });

   // Continue existing chat
   const response = await fetch('/api/v1/chat', {
     method: 'POST',
     body: JSON.stringify({
       message: userMessage,
       session_id: localStorage.getItem('session_id'),
       conversation_id: currentChatId
     })
   });
   ```

3. **Binding Display**
   ```javascript
   // Show binding status in UI
   if (response.is_chat_locked) {
     showBanner(`🔒 This chat is dedicated to: ${workflowName}`);
     disableWorkflowCreation();
   }
   ```

## Architecture Highlights

### Pydantic AI Best Practices
- ✅ Type-safe dependency injection via `WorkflowContext`
- ✅ Dynamic system prompts with `@agent.system_prompt`
- ✅ Context-aware constraint enforcement
- ✅ Stateless agent design

### MCP Best Practices
- ✅ Tools remain stateless
- ✅ Validation in API layer (not tool layer)
- ✅ Clean separation of concerns

### Storage Best Practices
- ✅ Atomic writes (temp file + rename)
- ✅ JSON format for human readability
- ✅ Automatic persistence and loading
- ✅ Graceful degradation on errors

## Troubleshooting

### Session not found
```bash
# Error: Session sess_123 not found
# Solution: Create session first
curl -X POST "http://localhost:8001/api/v1/sessions?user_identifier=user123"
```

### Workflow binding failed
```bash
# Error: Chat conv_123 is already bound to wf_approval
# This is expected behavior - start a new chat for a new workflow
```

### Can't create workflow in bound chat
```
AI Response: "This chat is dedicated to your 'Approval' workflow.
              To create a new workflow, please start a new chat."

# This is correct behavior - binding is enforced
```

## Future Enhancements

1. **Session Expiration**
   - Add TTL to sessions
   - Automatic cleanup of old sessions

2. **Session Authentication**
   - Link sessions to user accounts
   - JWT integration

3. **Workflow Sharing**
   - Share workflows across sessions
   - Team workspaces

4. **Chat Unbinding** (optional)
   - Allow unbinding under certain conditions
   - Requires careful UX consideration
