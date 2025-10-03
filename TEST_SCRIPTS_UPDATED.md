# Test Scripts Updated for Session Management

## Summary

The existing test scripts have been updated to support the new session management and chat-workflow binding features.

## Changes Made

### ✅ Updated Files

1. **`test_conversations.sh`** (English)
   - Added `create_session()` function
   - Added `MANAGER_SESSION_ID` and `NOVICE_SESSION_ID` variables
   - Updated `send_message()` to accept and include `session_id` parameter
   - Updated test functions to create sessions before chatting

2. **`test_conversations_es.sh`** (Spanish)
   - Added `create_session()` function
   - Added `GERENTE_SESSION_ID` and `NOVATO_SESSION_ID` variables
   - Updated `send_message()` to accept and include `session_id` parameter
   - Updated test functions to create sessions before chatting

### Breaking Change Addressed

**Before:**
```bash
send_message "Create a workflow" "$CONVERSATION_ID" "Manager"
# Missing session_id - would fail with 400 error
```

**After:**
```bash
SESSION_ID=$(create_session "manager_sarah")
send_message "Create a workflow" "$CONVERSATION_ID" "Manager" "$SESSION_ID"
# Now includes required session_id
```

## Test Execution

### Running Tests

**Option 1: Interactive Menu**
```bash
./run_tests.sh
# Choose from menu:
# 1 - Test Experienced Business Manager
# 2 - Test Novice User
# 3 - Run Full Conversation Test Suite
```

**Option 2: Direct Script Execution**
```bash
# English tests
./test_conversations.sh manager
./test_conversations.sh novice
./test_conversations.sh all

# Spanish tests
./test_conversations_es.sh gerente
./test_conversations_es.sh novato
./test_conversations_es.sh all
```

### Expected Behavior

**Manager Scenario (English):**
1. ✅ Creates session for "manager_sarah"
2. ✅ Creates first chat and supplier onboarding workflow
3. ✅ Chat becomes bound to supplier workflow
4. ✅ Attempts to create second workflow (customer returns)
5. ⚠️ **AI should refuse** and explain chat is bound
6. ✅ User would need new chat for second workflow

**Novice Scenario (English):**
1. ✅ Creates session for "novice_mike"
2. ✅ Creates chat for learning
3. ✅ Creates project management workflow
4. ✅ Chat becomes bound to project workflow
5. ✅ Can update bound workflow (add manager approval)
6. ❌ Cannot create new workflow in same chat

## Important Notes

### Session Creation
- Sessions are created at the start of each test persona
- User identifiers: `manager_sarah`, `novice_mike`, `gerente_maria`, `novato_carlos`
- Sessions persist across test runs (stored in `storage/sessions/`)

### Chat Binding Enforcement
The tests now demonstrate the one-workflow-per-chat rule:

```bash
# Test scenario that validates binding:
test_manager_persona() {
    SESSION_ID=$(create_session "manager_sarah")

    # First workflow creation - succeeds and binds chat
    send_message "Create supplier workflow..." "" "Manager" "$SESSION_ID"

    # Second workflow attempt - AI should politely refuse
    send_message "Create customer returns workflow..." "$CONVERSATION_ID" "Manager" "$SESSION_ID"
    # Expected AI response:
    # "This chat is dedicated to your 'Supplier Onboarding' workflow.
    #  To create a new workflow, please start a new chat in your session."
}
```

### Verification

After running tests, verify:
```bash
# Check sessions created
ls storage/sessions/
# Should see: sess_*.json files

# Check chat bindings
ls storage/chat_bindings/
# Should see: conv_*.json files

# Check workflows created
./test_conversations.sh verify
# or
./test_conversations_es.sh verificar
```

## Docker Requirement

⚠️ **Note:** Tests require Docker services to be running:

```bash
# Start services first
docker-compose up --build

# Then run tests
./run_tests.sh
```

## Troubleshooting

### Error: "session_id is required"
**Cause:** Old test script version
**Fix:** Test scripts are now updated - pull latest changes

### Error: "Session not found"
**Cause:** Session wasn't created or expired
**Fix:** Scripts now create sessions automatically

### AI creates multiple workflows in same chat
**Cause:** Binding constraint not enforced
**Fix:** Check that `WorkflowContext.is_workflow_bound` is being set correctly

### Tests still using old format
**Cause:** Running cached/old test scripts
**Fix:**
```bash
chmod +x test_conversations.sh test_conversations_es.sh
./test_conversations.sh all
```

## Next Steps

Once Docker is running, the test scripts will:

1. ✅ Create sessions for each persona
2. ✅ Test workflow creation with binding
3. ✅ Validate AI refuses multiple workflows per chat
4. ✅ Verify workflows are stored correctly
5. ✅ Test both English and Spanish scenarios

The tests are ready to validate the complete session management and binding implementation!
