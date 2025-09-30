"""
Tests for SystemPrompts modular prompt system.

Tests cover:
- Mode inference from user messages
- Prompt retrieval for each mode
- Token reduction calculations
- Agent integration with modular prompts
"""

import pytest

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.system_prompts import SystemPrompts, PromptMode
from agents.workflow_conversation_agent import WorkflowConversationAgent


class TestModeInference:
    """Test automatic mode detection from user messages."""

    def test_infer_creation_mode(self):
        """Detect creation intent from user messages."""
        creation_messages = [
            "Create a new workflow for me",
            "I need a workflow for approvals",
            "Can you make a task management process?",
            "Generate a workflow for document review",
            "Build me an incident workflow",
            "Set up a workflow for requests"
        ]

        for message in creation_messages:
            mode = SystemPrompts.infer_mode(message)
            assert mode == PromptMode.CREATION, f"Failed for: {message}"

    def test_infer_search_mode(self):
        """Detect search intent from user messages."""
        search_messages = [
            "Find workflows about approvals",
            "Show me available workflows",
            "List all workflows",
            "What workflows exist?",
            "Search for task workflows",
            "Get all existing workflows"
        ]

        for message in search_messages:
            mode = SystemPrompts.infer_mode(message)
            assert mode == PromptMode.SEARCH, f"Failed for: {message}"

    def test_infer_modification_mode(self):
        """Detect modification intent from user messages."""
        modification_messages = [
            "Update the approval workflow",
            "Modify this workflow",
            "Change the task states",
            "Add a new state to this workflow",
            "Remove the testing step",
            "Edit the workflow actions"
        ]

        for message in modification_messages:
            mode = SystemPrompts.infer_mode(message)
            assert mode == PromptMode.MODIFICATION, f"Failed for: {message}"

    def test_infer_analysis_mode(self):
        """Detect analysis intent from user messages."""
        analysis_messages = [
            "Explain this workflow",
            "What does this workflow do?",
            "How does the approval process work?",
            "Tell me about the states",
            "What can I do in this state?",
            "Describe the workflow"
        ]

        for message in analysis_messages:
            mode = SystemPrompts.infer_mode(message)
            assert mode == PromptMode.ANALYSIS, f"Failed for: {message}"

    def test_infer_general_mode_fallback(self):
        """Fall back to general mode for ambiguous messages."""
        general_messages = [
            "Hello",
            "I have a question",
            "Thanks",
            "Can you help me?",
            "What do you think?"
        ]

        for message in general_messages:
            mode = SystemPrompts.infer_mode(message, has_workflow=False)
            assert mode == PromptMode.GENERAL, f"Failed for: {message}"

    def test_infer_analysis_with_workflow_context(self):
        """Infer analysis mode when workflow context is available."""
        ambiguous_message = "Tell me more"

        # Without workflow: general
        mode_no_workflow = SystemPrompts.infer_mode(ambiguous_message, has_workflow=False)
        assert mode_no_workflow == PromptMode.GENERAL

        # With workflow: analysis
        mode_with_workflow = SystemPrompts.infer_mode(ambiguous_message, has_workflow=True)
        assert mode_with_workflow == PromptMode.ANALYSIS

    def test_multiple_patterns_highest_score(self):
        """Choose mode with highest pattern match score."""
        # Message with multiple intents, creation should win
        message = "Create a workflow and show me what you can do"
        mode = SystemPrompts.infer_mode(message)
        assert mode == PromptMode.CREATION


class TestPromptRetrieval:
    """Test prompt retrieval for different modes."""

    def test_get_general_prompt(self):
        """Retrieve general mode prompt."""
        prompt = SystemPrompts.get_prompt(PromptMode.GENERAL)

        assert len(prompt) > 0
        assert "business process consultant" in prompt.lower()
        assert "workflow" in prompt.lower()

    def test_get_creation_prompt(self):
        """Retrieve creation mode prompt."""
        prompt = SystemPrompts.get_prompt(PromptMode.CREATION)

        assert len(prompt) > 0
        assert "create" in prompt.lower() or "creation" in prompt.lower()
        assert "workflow" in prompt.lower()

    def test_get_search_prompt(self):
        """Retrieve search mode prompt."""
        prompt = SystemPrompts.get_prompt(PromptMode.SEARCH)

        assert len(prompt) > 0
        assert "search" in prompt.lower() or "find" in prompt.lower()
        assert "workflow" in prompt.lower()

    def test_get_modification_prompt(self):
        """Retrieve modification mode prompt."""
        prompt = SystemPrompts.get_prompt(PromptMode.MODIFICATION)

        assert len(prompt) > 0
        assert "modif" in prompt.lower() or "update" in prompt.lower()
        assert "workflow" in prompt.lower()

    def test_get_analysis_prompt(self):
        """Retrieve analysis mode prompt."""
        prompt = SystemPrompts.get_prompt(PromptMode.ANALYSIS)

        assert len(prompt) > 0
        assert "analysis" in prompt.lower() or "explain" in prompt.lower()
        assert "workflow" in prompt.lower()

    def test_prompts_are_different(self):
        """Each mode should have a distinct prompt."""
        prompts = {
            mode: SystemPrompts.get_prompt(mode)
            for mode in PromptMode
        }

        # All prompts should be unique
        prompt_set = set(prompts.values())
        assert len(prompt_set) == len(PromptMode)

    def test_get_prompt_for_message(self):
        """Get appropriate prompt with mode inference."""
        message = "Create a new workflow"
        prompt, mode = SystemPrompts.get_prompt_for_message(message)

        assert mode == PromptMode.CREATION
        assert len(prompt) > 0
        assert "create" in prompt.lower() or "creation" in prompt.lower()


class TestTokenReduction:
    """Test token reduction calculations."""

    def test_get_mode_stats(self):
        """Get token statistics for each mode."""
        stats = SystemPrompts.get_mode_stats()

        assert "general" in stats
        assert "creation" in stats
        assert "search" in stats
        assert "modification" in stats
        assert "analysis" in stats
        assert "baseline" in stats

        # Baseline should be 2000 (monolithic prompt)
        assert stats["baseline"] == 2000

        # Each mode should be less than baseline
        for mode in ["general", "creation", "search", "modification", "analysis"]:
            assert stats[mode] < stats["baseline"]

    def test_token_reduction_calculation(self):
        """Calculate token reduction percentage."""
        for mode in PromptMode:
            reduction = SystemPrompts.get_token_reduction(mode)

            assert 0 <= reduction <= 100
            # Should have significant reduction (at least 40%)
            assert reduction >= 40

    def test_general_mode_token_count(self):
        """General mode should be ~400 tokens."""
        stats = SystemPrompts.get_mode_stats()
        assert stats["general"] == 400

    def test_creation_mode_token_count(self):
        """Creation mode should be ~700 tokens."""
        stats = SystemPrompts.get_mode_stats()
        assert stats["creation"] == 700

    def test_search_mode_token_count(self):
        """Search mode should be ~650 tokens."""
        stats = SystemPrompts.get_mode_stats()
        assert stats["search"] == 650

    def test_modification_mode_token_count(self):
        """Modification mode should be ~600 tokens."""
        stats = SystemPrompts.get_mode_stats()
        assert stats["modification"] == 600

    def test_analysis_mode_token_count(self):
        """Analysis mode should be ~550 tokens."""
        stats = SystemPrompts.get_mode_stats()
        assert stats["analysis"] == 550


class TestAgentIntegration:
    """Test SystemPrompts integration with WorkflowConversationAgent."""

    def test_agent_with_modular_prompts_enabled(self):
        """Create agent with modular prompts enabled."""
        agent = WorkflowConversationAgent(test_mode=True, use_modular_prompts=True)

        assert agent.use_modular_prompts is True
        assert agent.current_mode is None  # No conversation yet

    def test_agent_with_modular_prompts_disabled(self):
        """Create agent with modular prompts disabled (legacy mode)."""
        agent = WorkflowConversationAgent(test_mode=True, use_modular_prompts=False)

        assert agent.use_modular_prompts is False

    def test_agent_get_current_mode(self):
        """Get current mode from agent."""
        agent = WorkflowConversationAgent(test_mode=True, use_modular_prompts=True)

        mode = agent.get_current_mode()
        assert mode is None  # No conversation yet

    def test_agent_get_mode_info_no_mode(self):
        """Get mode info when no mode set."""
        agent = WorkflowConversationAgent(test_mode=True, use_modular_prompts=True)

        info = agent.get_mode_info()
        assert info["mode"] == "none"
        assert info["token_estimate"] == 0
        assert info["token_reduction"] == 0.0

    def test_enhance_message_with_mode(self):
        """Enhance message with mode-specific guidance."""
        agent = WorkflowConversationAgent(test_mode=True, use_modular_prompts=True)

        message = "Create a workflow"
        enhanced = agent._enhance_message_with_mode(message, PromptMode.CREATION)

        assert "CREATION" in enhanced
        assert message in enhanced
        assert len(enhanced) > len(message)

    def test_enhance_message_disabled(self):
        """Message enhancement should be bypassed when disabled."""
        agent = WorkflowConversationAgent(test_mode=True, use_modular_prompts=False)

        message = "Create a workflow"
        enhanced = agent._enhance_message_with_mode(message, PromptMode.CREATION)

        # Should return original message unchanged
        assert enhanced == message


class TestPromptTokenBenchmark:
    """Benchmark token reduction across different modes."""

    def test_average_token_reduction(self):
        """Calculate average token reduction across all modes."""
        total_reduction = 0
        mode_count = len(PromptMode)

        for mode in PromptMode:
            reduction = SystemPrompts.get_token_reduction(mode)
            total_reduction += reduction

        avg_reduction = total_reduction / mode_count

        # Should achieve 40-60% average reduction
        assert 40 <= avg_reduction <= 70

    def test_token_savings_vs_baseline(self):
        """Calculate total token savings compared to baseline."""
        stats = SystemPrompts.get_mode_stats()
        baseline = stats["baseline"]

        # Calculate weighted average based on typical usage
        # Assume: 30% creation, 20% search, 15% modification, 20% analysis, 15% general
        weighted_tokens = (
            stats["creation"] * 0.30 +
            stats["search"] * 0.20 +
            stats["modification"] * 0.15 +
            stats["analysis"] * 0.20 +
            stats["general"] * 0.15
        )

        savings_percent = ((baseline - weighted_tokens) / baseline) * 100

        # Should save at least 50% on average
        assert savings_percent >= 50

    def test_all_modes_under_800_tokens(self):
        """All modes should be under 800 tokens."""
        stats = SystemPrompts.get_mode_stats()

        for mode in ["general", "creation", "search", "modification", "analysis"]:
            assert stats[mode] <= 800, f"{mode} exceeds 800 tokens: {stats[mode]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])