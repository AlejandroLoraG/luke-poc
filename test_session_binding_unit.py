#!/usr/bin/env python3
"""
Unit tests for session management and chat binding features.
Tests core functionality without requiring running services.
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-agent', 'src'))

from core.models import Session, ChatBinding, ConversationTurn
from core.session_manager import SessionManager
from core.chat_binding_manager import ChatBindingManager


def test_session_model():
    """Test Session data model."""
    print("\n🧪 Testing Session Model...")

    session = Session(
        session_id="sess_test123",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        user_identifier="test_user"
    )

    assert session.session_id == "sess_test123"
    assert session.user_identifier == "test_user"

    # Test update activity
    old_activity = session.last_activity
    session.update_activity()
    assert session.last_activity > old_activity

    print("   ✅ Session model works correctly")


def test_chat_binding_model():
    """Test ChatBinding data model."""
    print("\n🧪 Testing ChatBinding Model...")

    binding = ChatBinding(
        conversation_id="conv_test123",
        session_id="sess_test123",
        created_at=datetime.now()
    )

    # Initially not bound
    assert not binding.is_bound()
    assert binding.can_create_workflow()
    assert binding.bound_workflow_id is None

    # Bind to workflow
    binding.bind("wf_approval")
    assert binding.is_bound()
    assert not binding.can_create_workflow()
    assert binding.bound_workflow_id == "wf_approval"
    assert binding.binding_locked_at is not None

    # Try to bind again (should raise error)
    try:
        binding.bind("wf_another")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "already bound" in str(e)

    print("   ✅ ChatBinding model works correctly")


def test_session_manager():
    """Test SessionManager with temp storage."""
    print("\n🧪 Testing SessionManager...")

    # Create temp directory for testing
    temp_dir = tempfile.mkdtemp()

    try:
        # Create manager
        manager = SessionManager(storage_dir=temp_dir)

        # Create session
        session = manager.create_session("test_user_1")
        assert session.session_id.startswith("sess_")
        assert session.user_identifier == "test_user_1"

        # Retrieve session
        retrieved = manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

        # Update activity
        success = manager.update_activity(session.session_id)
        assert success

        # List sessions
        sessions = manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == session.session_id

        # Create another manager (test persistence)
        manager2 = SessionManager(storage_dir=temp_dir)
        retrieved2 = manager2.get_session(session.session_id)
        assert retrieved2 is not None
        assert retrieved2.session_id == session.session_id

        # Get stats
        stats = manager.get_stats()
        assert stats["total_sessions"] == 1

        # Delete session
        success = manager.delete_session(session.session_id)
        assert success
        assert manager.get_session(session.session_id) is None

        print("   ✅ SessionManager works correctly")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_chat_binding_manager():
    """Test ChatBindingManager with temp storage."""
    print("\n🧪 Testing ChatBindingManager...")

    # Create temp directory for testing
    temp_dir = tempfile.mkdtemp()

    try:
        # Create manager
        manager = ChatBindingManager(storage_dir=temp_dir)

        # Create binding
        binding = manager.create_binding("conv_123", "sess_abc")
        assert binding.conversation_id == "conv_123"
        assert binding.session_id == "sess_abc"
        assert not binding.is_bound()

        # Retrieve binding
        retrieved = manager.get_binding("conv_123")
        assert retrieved is not None
        assert retrieved.conversation_id == "conv_123"

        # Check not bound
        assert not manager.is_bound("conv_123")
        assert manager.get_bound_workflow("conv_123") is None

        # Bind workflow
        bound = manager.bind_workflow("conv_123", "wf_approval")
        assert bound.is_bound()
        assert bound.bound_workflow_id == "wf_approval"

        # Check bound
        assert manager.is_bound("conv_123")
        assert manager.get_bound_workflow("conv_123") == "wf_approval"

        # Try to bind again (should raise error)
        try:
            manager.bind_workflow("conv_123", "wf_another")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected

        # Create another binding in same session
        binding2 = manager.create_binding("conv_456", "sess_abc")
        manager.bind_workflow("conv_456", "wf_onboarding")

        # Get session bindings
        session_bindings = manager.get_session_bindings("sess_abc")
        assert len(session_bindings) == 2

        # Test persistence
        manager2 = ChatBindingManager(storage_dir=temp_dir)
        retrieved2 = manager2.get_binding("conv_123")
        assert retrieved2 is not None
        assert retrieved2.bound_workflow_id == "wf_approval"

        # Get stats
        stats = manager.get_stats()
        assert stats["total_bindings"] == 2
        assert stats["bound_count"] == 2

        print("   ✅ ChatBindingManager works correctly")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_workflow_context_enhancements():
    """Test WorkflowContext enhancements."""
    print("\n🧪 Testing WorkflowContext Enhancements...")

    try:
        from agents.workflow_conversation_agent import WorkflowContext

        # Create context with binding info
        context = WorkflowContext(
            conversation_id="conv_123",
            session_id="sess_abc",
            bound_workflow_id="wf_approval",
            is_workflow_bound=True
        )

        assert context.session_id == "sess_abc"
        assert context.bound_workflow_id == "wf_approval"
        assert context.is_workflow_bound
        assert not context.can_create_new_workflow()

        # Context without binding
        context2 = WorkflowContext(
            conversation_id="conv_456",
            session_id="sess_abc",
            is_workflow_bound=False
        )

        assert not context2.is_workflow_bound
        assert context2.can_create_new_workflow()

        print("   ✅ WorkflowContext enhancements work correctly")
    except ModuleNotFoundError:
        print("   ⚠️  Skipped (requires pydantic_ai - run in Docker)")


def test_conversation_turn_enhancement():
    """Test ConversationTurn enhancement."""
    print("\n🧪 Testing ConversationTurn Enhancement...")

    turn = ConversationTurn(
        user_message="Create a workflow",
        agent_response="Created workflow",
        timestamp=datetime.now(),
        mcp_tools_used=["create_workflow"],
        workflow_id="wf_approval"
    )

    assert turn.workflow_id == "wf_approval"
    assert turn.mcp_tools_used == ["create_workflow"]

    print("   ✅ ConversationTurn enhancement works correctly")


def run_all_tests():
    """Run all unit tests."""
    print("=" * 70)
    print("Running Session & Binding Unit Tests")
    print("=" * 70)

    tests = [
        test_session_model,
        test_chat_binding_model,
        test_session_manager,
        test_chat_binding_manager,
        test_workflow_context_enhancements,
        test_conversation_turn_enhancement
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"   ❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
