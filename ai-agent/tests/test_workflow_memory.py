"""
Tests for WorkflowMemory - lightweight workflow tracking in conversations.

Tests cover:
- Workflow reference management (add, get, search)
- LRU tracking and trimming
- Alias generation and search
- Context formatting
- ConversationManager integration
"""

import pytest
from datetime import datetime
import time

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.workflow_memory import WorkflowMemory, WorkflowReference
from core.conversation_manager import ConversationManager


class TestWorkflowReference:
    """Test WorkflowReference dataclass."""

    def test_workflow_reference_creation(self):
        """Create a workflow reference with basic fields."""
        ref = WorkflowReference(
            spec_id="wf_test",
            name="Test Workflow",
            action="created",
            timestamp=datetime.now()
        )

        assert ref.spec_id == "wf_test"
        assert ref.name == "Test Workflow"
        assert ref.action == "created"
        assert isinstance(ref.timestamp, datetime)
        assert ref.aliases == []
        assert ref.tags == set()

    def test_workflow_reference_with_aliases_and_tags(self):
        """Create workflow reference with aliases and tags."""
        ref = WorkflowReference(
            spec_id="wf_test",
            name="Document Approval",
            action="discussed",
            timestamp=datetime.now(),
            aliases=["doc approval", "document", "approval"],
            tags={"workflow", "approval", "documents"}
        )

        assert len(ref.aliases) == 3
        assert "doc approval" in ref.aliases
        assert len(ref.tags) == 3
        assert "workflow" in ref.tags


class TestWorkflowMemory:
    """Test WorkflowMemory class functionality."""

    def test_add_and_get_workflow(self):
        """Add and retrieve a workflow."""
        memory = WorkflowMemory()

        memory.add_workflow(
            spec_id="wf_test",
            name="Test Workflow",
            action="created"
        )

        ref = memory.get_workflow("wf_test")
        assert ref is not None
        assert ref.spec_id == "wf_test"
        assert ref.name == "Test Workflow"
        assert ref.action == "created"

    def test_get_nonexistent_workflow(self):
        """Getting non-existent workflow returns None."""
        memory = WorkflowMemory()

        ref = memory.get_workflow("nonexistent")
        assert ref is None

    def test_update_existing_workflow(self):
        """Updating workflow should replace reference."""
        memory = WorkflowMemory()

        # Add initial
        memory.add_workflow("wf_test", "Test Workflow", "created")

        # Update
        memory.add_workflow("wf_test", "Updated Workflow", "modified")

        ref = memory.get_workflow("wf_test")
        assert ref.name == "Updated Workflow"
        assert ref.action == "modified"

    def test_lru_tracking_on_add(self):
        """Adding workflow should update LRU order."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_1", "Workflow 1", "created")
        memory.add_workflow("wf_2", "Workflow 2", "created")
        memory.add_workflow("wf_3", "Workflow 3", "created")

        # Get recent workflows - should be in reverse order of addition
        recent = memory.get_recent_workflows(limit=3)
        assert len(recent) == 3
        assert recent[0].spec_id == "wf_3"
        assert recent[1].spec_id == "wf_2"
        assert recent[2].spec_id == "wf_1"

    def test_lru_tracking_on_get(self):
        """Getting workflow should update LRU order."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_1", "Workflow 1", "created")
        memory.add_workflow("wf_2", "Workflow 2", "created")
        memory.add_workflow("wf_3", "Workflow 3", "created")

        # Access wf_1 - should move to most recent
        memory.get_workflow("wf_1")

        recent = memory.get_recent_workflows(limit=3)
        assert recent[0].spec_id == "wf_1"  # Most recent
        assert recent[1].spec_id == "wf_3"
        assert recent[2].spec_id == "wf_2"

    def test_max_references_trimming(self):
        """Exceeding max references should trim oldest."""
        memory = WorkflowMemory(max_references=3)

        # Add 5 workflows
        for i in range(5):
            memory.add_workflow(f"wf_{i}", f"Workflow {i}", "created")

        # Should only have last 3
        stats = memory.get_stats()
        assert stats["total_workflows"] == 3

        # First two should be removed
        assert memory.get_workflow("wf_0") is None
        assert memory.get_workflow("wf_1") is None

        # Last three should exist
        assert memory.get_workflow("wf_2") is not None
        assert memory.get_workflow("wf_3") is not None
        assert memory.get_workflow("wf_4") is not None

    def test_alias_generation(self):
        """Aliases should be auto-generated from workflow name."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_test", "Document Approval Process")

        ref = memory.get_workflow("wf_test")
        assert len(ref.aliases) > 0

        # Should include lowercase full name
        assert "document approval process" in ref.aliases

        # Should include individual words
        assert "document" in ref.aliases or any("document" in a for a in ref.aliases)

    def test_search_by_name(self):
        """Search workflows by name."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_1", "Document Approval", "created")
        memory.add_workflow("wf_2", "Task Management", "created")
        memory.add_workflow("wf_3", "Document Review", "created")

        # Search for "document"
        results = memory.search_workflows("document")
        assert len(results) == 2

        spec_ids = [r.spec_id for r in results]
        assert "wf_1" in spec_ids
        assert "wf_3" in spec_ids

    def test_search_by_alias(self):
        """Search workflows by alias."""
        memory = WorkflowMemory()

        memory.add_workflow(
            "wf_test",
            "Document Approval",
            "created",
            aliases=["doc approval", "doc", "approval"]
        )

        # Search using alias
        results = memory.search_workflows("doc")
        assert len(results) == 1
        assert results[0].spec_id == "wf_test"

    def test_search_case_insensitive(self):
        """Search should be case-insensitive."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_test", "Document Approval", "created")

        # Different case variations
        assert len(memory.search_workflows("document")) > 0
        assert len(memory.search_workflows("DOCUMENT")) > 0
        assert len(memory.search_workflows("Document")) > 0

    def test_get_recent_workflows(self):
        """Get recent workflows with limit."""
        memory = WorkflowMemory()

        # Add 10 workflows
        for i in range(10):
            memory.add_workflow(f"wf_{i}", f"Workflow {i}", "created")
            time.sleep(0.001)  # Ensure different timestamps

        # Get last 5
        recent = memory.get_recent_workflows(limit=5)
        assert len(recent) == 5

        # Should be most recent first
        assert recent[0].spec_id == "wf_9"
        assert recent[4].spec_id == "wf_5"

    def test_get_workflows_by_action(self):
        """Filter workflows by action type."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_1", "Workflow 1", "created")
        memory.add_workflow("wf_2", "Workflow 2", "modified")
        memory.add_workflow("wf_3", "Workflow 3", "created")
        memory.add_workflow("wf_4", "Workflow 4", "discussed")

        # Get created workflows
        created = memory.get_workflows_by_action("created")
        assert len(created) == 2

        spec_ids = [r.spec_id for r in created]
        assert "wf_1" in spec_ids
        assert "wf_3" in spec_ids

    def test_get_workflows_by_tag(self):
        """Filter workflows by tag."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_1", "Workflow 1", "created", tags={"approval", "document"})
        memory.add_workflow("wf_2", "Workflow 2", "created", tags={"task", "management"})
        memory.add_workflow("wf_3", "Workflow 3", "created", tags={"approval", "request"})

        # Get workflows with "approval" tag
        approval_workflows = memory.get_workflows_by_tag("approval")
        assert len(approval_workflows) == 2

        spec_ids = [r.spec_id for r in approval_workflows]
        assert "wf_1" in spec_ids
        assert "wf_3" in spec_ids

    def test_format_for_context(self):
        """Format workflows for context window."""
        memory = WorkflowMemory()

        memory.add_workflow("wf_1", "Document Approval", "created")
        memory.add_workflow("wf_2", "Task Management", "modified")
        memory.add_workflow("wf_3", "Request Handling", "discussed")

        context = memory.format_for_context(limit=3)

        assert "Recent workflows:" in context
        assert "Document Approval" in context
        assert "wf_1" in context
        assert "created" in context

    def test_format_for_context_empty(self):
        """Format for context when no workflows."""
        memory = WorkflowMemory()

        context = memory.format_for_context()
        assert context == ""

    def test_get_stats(self):
        """Get memory statistics."""
        memory = WorkflowMemory(max_references=50)

        memory.add_workflow("wf_1", "Workflow 1", "created", tags={"tag1", "tag2"})
        memory.add_workflow("wf_2", "Workflow 2", "modified", tags={"tag2", "tag3"})
        memory.add_workflow("wf_3", "Workflow 3", "discussed", tags={"tag1"})

        stats = memory.get_stats()

        assert stats["total_workflows"] == 3
        assert stats["max_references"] == 50
        assert "actions_count" in stats
        assert stats["actions_count"]["created"] == 1
        assert stats["actions_count"]["modified"] == 1
        assert stats["actions_count"]["discussed"] == 1
        assert stats["total_tags"] == 3
        assert "tag1" in stats["tags"]

    def test_clear_memory(self):
        """Clear all workflow references."""
        memory = WorkflowMemory()

        # Add workflows
        for i in range(5):
            memory.add_workflow(f"wf_{i}", f"Workflow {i}", "created")

        assert memory.get_stats()["total_workflows"] == 5

        # Clear
        memory.clear()

        assert memory.get_stats()["total_workflows"] == 0
        assert memory.get_workflow("wf_0") is None

    def test_export_references(self):
        """Export workflow references as dictionaries."""
        memory = WorkflowMemory()

        memory.add_workflow(
            "wf_test",
            "Test Workflow",
            "created",
            aliases=["test", "workflow"],
            tags={"tag1", "tag2"}
        )

        exported = memory.export_references()
        assert len(exported) == 1
        assert exported[0]["spec_id"] == "wf_test"
        assert exported[0]["name"] == "Test Workflow"
        assert exported[0]["action"] == "created"
        assert "timestamp" in exported[0]
        assert len(exported[0]["aliases"]) > 0
        assert len(exported[0]["tags"]) == 2

    def test_import_references(self):
        """Import workflow references from dictionaries."""
        memory = WorkflowMemory()

        references = [
            {
                "spec_id": "wf_1",
                "name": "Workflow 1",
                "action": "created",
                "timestamp": datetime.now().isoformat(),
                "aliases": ["wf1", "one"],
                "tags": ["tag1"]
            },
            {
                "spec_id": "wf_2",
                "name": "Workflow 2",
                "action": "modified",
                "timestamp": datetime.now().isoformat(),
                "aliases": ["wf2"],
                "tags": ["tag2"]
            }
        ]

        memory.import_references(references)

        assert memory.get_stats()["total_workflows"] == 2
        assert memory.get_workflow("wf_1") is not None
        assert memory.get_workflow("wf_2") is not None


class TestConversationManagerWorkflowMemory:
    """Test WorkflowMemory integration with ConversationManager."""

    def test_get_workflow_memory(self):
        """Get workflow memory for a conversation."""
        manager = ConversationManager()

        memory = manager.get_workflow_memory("test_conv")
        assert memory is not None
        assert isinstance(memory, WorkflowMemory)

    def test_workflow_memory_per_conversation(self):
        """Each conversation should have independent memory."""
        manager = ConversationManager()

        # Add workflows to different conversations
        manager.track_workflow("conv_1", "wf_1", "Workflow 1", "created")
        manager.track_workflow("conv_2", "wf_2", "Workflow 2", "created")

        # Verify independence
        memory1 = manager.get_workflow_memory("conv_1")
        memory2 = manager.get_workflow_memory("conv_2")

        assert memory1.get_workflow("wf_1") is not None
        assert memory1.get_workflow("wf_2") is None

        assert memory2.get_workflow("wf_2") is not None
        assert memory2.get_workflow("wf_1") is None

    def test_track_workflow(self):
        """Track workflow in conversation."""
        manager = ConversationManager()

        manager.track_workflow(
            "test_conv",
            spec_id="wf_test",
            name="Test Workflow",
            action="created"
        )

        memory = manager.get_workflow_memory("test_conv")
        ref = memory.get_workflow("wf_test")

        assert ref is not None
        assert ref.spec_id == "wf_test"
        assert ref.name == "Test Workflow"
        assert ref.action == "created"

    def test_track_workflow_with_aliases_and_tags(self):
        """Track workflow with aliases and tags."""
        manager = ConversationManager()

        manager.track_workflow(
            "test_conv",
            spec_id="wf_test",
            name="Document Approval",
            action="created",
            aliases=["doc approval"],
            tags={"approval", "document"}
        )

        memory = manager.get_workflow_memory("test_conv")
        ref = memory.get_workflow("wf_test")

        assert "doc approval" in ref.aliases
        assert "approval" in ref.tags

    def test_get_workflow_context(self):
        """Get formatted workflow context."""
        manager = ConversationManager()

        # Track multiple workflows
        manager.track_workflow("test_conv", "wf_1", "Workflow 1", "created")
        manager.track_workflow("test_conv", "wf_2", "Workflow 2", "modified")

        context = manager.get_workflow_context("test_conv", limit=2)

        assert "Recent workflows:" in context
        assert "Workflow 1" in context
        assert "Workflow 2" in context

    def test_workflow_memory_persists_across_turns(self):
        """Workflow memory should persist across conversation turns."""
        manager = ConversationManager()

        # Track workflow
        manager.track_workflow("test_conv", "wf_test", "Test Workflow", "created")

        # Add conversation turns
        manager.add_turn("test_conv", "Hello", "Hi", [])
        manager.add_turn("test_conv", "How are you?", "Good", [])

        # Workflow memory should still exist
        memory = manager.get_workflow_memory("test_conv")
        assert memory.get_workflow("wf_test") is not None


class TestAliasGeneration:
    """Test alias generation logic."""

    def test_generate_aliases_simple(self):
        """Generate aliases for simple workflow name."""
        memory = WorkflowMemory()
        memory.add_workflow("wf_test", "Task Management")

        ref = memory.get_workflow("wf_test")
        aliases = ref.aliases

        # Should include lowercase full name
        assert "task management" in aliases

        # Should include individual words
        assert "task" in aliases
        assert "management" in aliases

    def test_generate_aliases_with_abbreviations(self):
        """Generate aliases with common abbreviations."""
        memory = WorkflowMemory()
        memory.add_workflow("wf_test", "Document Approval Process")

        ref = memory.get_workflow("wf_test")
        aliases = ref.aliases

        # Should include abbreviations
        abbreviated_forms = [a for a in aliases if "doc" in a or "appr" in a or "proc" in a]
        assert len(abbreviated_forms) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])