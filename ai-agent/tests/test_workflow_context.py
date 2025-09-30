"""
Unit tests for WorkflowContext dataclass.

Tests the type-safe context structure following Pydantic AI patterns.
"""

import pytest
from src.agents.workflow_conversation_agent import WorkflowContext


def test_workflow_context_creation():
    """Test basic WorkflowContext creation with defaults."""
    ctx = WorkflowContext()

    assert ctx.conversation_id == ""
    assert ctx.turn_count == 0
    assert ctx.workflow_spec is None
    assert ctx.conversation_workflows == []
    assert ctx.tenant_id == "luke_123"
    assert ctx.user_id is None


def test_workflow_context_with_values():
    """Test WorkflowContext creation with explicit values."""
    workflow_spec = {
        "specId": "wf_test",
        "name": "Test Workflow",
        "states": []
    }

    ctx = WorkflowContext(
        conversation_id="conv-123",
        turn_count=5,
        workflow_spec=workflow_spec,
        tenant_id="custom_tenant"
    )

    assert ctx.conversation_id == "conv-123"
    assert ctx.turn_count == 5
    assert ctx.workflow_spec == workflow_spec
    assert ctx.tenant_id == "custom_tenant"


def test_workflow_context_with_workflow_spec():
    """Test WorkflowContext with a full workflow specification."""
    spec = {
        "specId": "wf_approval",
        "name": "Approval Process",
        "states": [
            {"slug": "submitted", "name": "Submitted", "type": "initial"},
            {"slug": "approved", "name": "Approved", "type": "final"}
        ],
        "actions": [
            {"slug": "approve", "from": "submitted", "to": "approved"}
        ]
    }

    ctx = WorkflowContext(workflow_spec=spec)

    assert ctx.workflow_spec["specId"] == "wf_approval"
    assert ctx.workflow_spec["name"] == "Approval Process"
    assert len(ctx.workflow_spec["states"]) == 2


def test_add_workflow_reference():
    """Test adding workflow references to the context."""
    ctx = WorkflowContext(conversation_id="conv-1")

    # Add first reference
    ctx.add_workflow_reference("wf_123", "Task Management", "created")

    assert len(ctx.conversation_workflows) == 1
    assert ctx.conversation_workflows[0]["spec_id"] == "wf_123"
    assert ctx.conversation_workflows[0]["name"] == "Task Management"
    assert ctx.conversation_workflows[0]["action"] == "created"

    # Add second reference
    ctx.add_workflow_reference("wf_456", "Approval Process", "modified")

    assert len(ctx.conversation_workflows) == 2
    assert ctx.conversation_workflows[1]["spec_id"] == "wf_456"
    assert ctx.conversation_workflows[1]["action"] == "modified"


def test_get_recent_workflows():
    """Test retrieving recent workflow references."""
    ctx = WorkflowContext()

    # Add multiple workflows
    for i in range(10):
        ctx.add_workflow_reference(f"wf_{i}", f"Workflow {i}", "created")

    # Get last 3
    recent = ctx.get_recent_workflows(limit=3)

    assert len(recent) == 3
    assert recent[0]["spec_id"] == "wf_7"
    assert recent[1]["spec_id"] == "wf_8"
    assert recent[2]["spec_id"] == "wf_9"


def test_get_recent_workflows_with_fewer_than_limit():
    """Test get_recent_workflows when fewer workflows exist than limit."""
    ctx = WorkflowContext()

    ctx.add_workflow_reference("wf_1", "Workflow 1", "created")
    ctx.add_workflow_reference("wf_2", "Workflow 2", "created")

    recent = ctx.get_recent_workflows(limit=5)

    assert len(recent) == 2
    assert recent[0]["spec_id"] == "wf_1"
    assert recent[1]["spec_id"] == "wf_2"


def test_get_recent_workflows_empty():
    """Test get_recent_workflows with no workflows."""
    ctx = WorkflowContext()

    recent = ctx.get_recent_workflows(limit=5)

    assert recent == []


def test_immutable_defaults():
    """Test that default factory works correctly (no shared state)."""
    ctx1 = WorkflowContext()
    ctx2 = WorkflowContext()

    ctx1.add_workflow_reference("wf_1", "Test", "created")

    # ctx2 should not be affected by ctx1's modifications
    assert len(ctx1.conversation_workflows) == 1
    assert len(ctx2.conversation_workflows) == 0


def test_workflow_context_dataclass_fields():
    """Test that WorkflowContext has proper dataclass structure."""
    from dataclasses import fields

    ctx_fields = {f.name: f.type for f in fields(WorkflowContext)}

    # Verify expected fields exist
    assert "conversation_id" in ctx_fields
    assert "turn_count" in ctx_fields
    assert "workflow_spec" in ctx_fields
    assert "conversation_workflows" in ctx_fields
    assert "tenant_id" in ctx_fields
    assert "user_id" in ctx_fields


def test_multiple_actions_on_same_workflow():
    """Test tracking multiple actions on the same workflow."""
    ctx = WorkflowContext(conversation_id="conv-1")

    # Same workflow, different actions
    ctx.add_workflow_reference("wf_123", "Task Management", "created")
    ctx.add_workflow_reference("wf_123", "Task Management", "modified")
    ctx.add_workflow_reference("wf_123", "Task Management", "discussed")

    assert len(ctx.conversation_workflows) == 3
    assert all(w["spec_id"] == "wf_123" for w in ctx.conversation_workflows)
    assert ctx.conversation_workflows[0]["action"] == "created"
    assert ctx.conversation_workflows[1]["action"] == "modified"
    assert ctx.conversation_workflows[2]["action"] == "discussed"


def test_workflow_context_repr():
    """Test that WorkflowContext has a reasonable string representation."""
    ctx = WorkflowContext(
        conversation_id="conv-123",
        turn_count=5
    )

    repr_str = repr(ctx)

    # Should contain key information
    assert "WorkflowContext" in repr_str
    assert "conv-123" in repr_str
    assert "5" in repr_str or "turn_count=5" in repr_str