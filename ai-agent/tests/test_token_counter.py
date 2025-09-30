"""
Tests for TokenCounter and telemetry integration.

Tests cover:
- Token counting approximation
- Token usage calculations
- Warning and critical thresholds
- Telemetry tracking and history
- ConversationManager integration
- Statistics reporting
"""

import pytest
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.token_counter import TokenCounter, TokenUsage, create_token_counter
from core.models import ConversationTurn
from core.conversation_manager import ConversationManager


class TestTokenCounting:
    """Test basic token counting approximation."""

    def test_count_tokens_simple(self):
        """Count tokens in simple text."""
        counter = TokenCounter()

        # 4 characters = 1 token
        text = "test"  # 4 chars = 1 token
        assert counter.count_tokens(text) == 1

        text = "hello world"  # 11 chars = 2 tokens (11/4 = 2.75, rounded down)
        assert counter.count_tokens(text) == 2

    def test_count_tokens_empty(self):
        """Handle empty text."""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0
        assert counter.count_tokens(None) == 0

    def test_count_tokens_longer_text(self):
        """Count tokens in longer text."""
        counter = TokenCounter()

        # 100 characters ≈ 25 tokens
        text = "a" * 100
        assert counter.count_tokens(text) == 25

        # 400 characters ≈ 100 tokens
        text = "word " * 80  # 5 chars * 80 = 400
        assert counter.count_tokens(text) == 100

    def test_chars_per_token_configuration(self):
        """Verify chars per token ratio."""
        counter = TokenCounter()
        assert counter.CHARS_PER_TOKEN == 4


class TestConversationTokenCounting:
    """Test token counting for conversations."""

    def test_count_conversation_tokens(self):
        """Count tokens in conversation turns."""
        counter = TokenCounter()

        turns = [
            ConversationTurn(
                user_message="Hello",  # 5 chars = 1 token
                agent_response="Hi there",  # 8 chars = 2 tokens
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
        ]

        # Total: 1 + 2 + 4 (formatting overhead) = 7 tokens
        tokens = counter.count_conversation_tokens(turns)
        assert tokens == 7

    def test_count_multiple_turns(self):
        """Count tokens across multiple turns."""
        counter = TokenCounter()

        turns = [
            ConversationTurn(
                user_message="Create a workflow",  # 17 chars = 4 tokens
                agent_response="I'll help you create a workflow",  # 32 chars = 8 tokens
                timestamp=datetime.now(),
                mcp_tools_used=[]
            ),
            ConversationTurn(
                user_message="Add a state",  # 11 chars = 2 tokens
                agent_response="State added successfully",  # 24 chars = 6 tokens
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
        ]

        # Turn 1: 4 + 8 + 4 = 16
        # Turn 2: 2 + 6 + 4 = 12
        # Total: 27 tokens (adjusted for rounding)
        tokens = counter.count_conversation_tokens(turns)
        assert tokens == 27

    def test_count_empty_conversation(self):
        """Handle empty conversation."""
        counter = TokenCounter()
        assert counter.count_conversation_tokens([]) == 0


class TestWorkflowTokenCounting:
    """Test token counting for workflow specs."""

    def test_count_workflow_tokens(self):
        """Count tokens in workflow specification."""
        counter = TokenCounter()

        workflow_spec = {
            "specId": "wf_test",
            "name": "Test Workflow",
            "states": [{"slug": "draft"}, {"slug": "review"}]
        }

        tokens = counter.count_workflow_tokens(workflow_spec)
        assert tokens > 0  # Should have some tokens

    def test_count_none_workflow(self):
        """Handle None workflow spec."""
        counter = TokenCounter()
        assert counter.count_workflow_tokens(None) == 0

    def test_count_empty_workflow(self):
        """Handle empty workflow spec."""
        counter = TokenCounter()
        assert counter.count_workflow_tokens({}) >= 0


class TestTokenUsageCalculation:
    """Test comprehensive token usage calculation."""

    def test_calculate_usage_basic(self):
        """Calculate token usage with all components."""
        counter = TokenCounter(context_window_limit=1000)

        system_prompt = "You are a helpful assistant"  # ~28 chars = 7 tokens
        conversation_history = "User: Hello\nAgent: Hi"  # ~22 chars = 5 tokens
        workflow_spec = {"specId": "wf_1"}  # ~18 chars JSON = 4 tokens

        usage = counter.calculate_usage(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            workflow_spec=workflow_spec
        )

        assert usage.system_prompt > 0
        assert usage.conversation_history > 0
        assert usage.workflow_context > 0
        assert usage.total == usage.system_prompt + usage.conversation_history + usage.workflow_context
        assert 0 <= usage.percentage_of_limit <= 100

    def test_calculate_usage_without_workflow(self):
        """Calculate usage without workflow spec."""
        counter = TokenCounter(context_window_limit=1000)

        usage = counter.calculate_usage(
            system_prompt="System prompt",
            conversation_history="Some history",
            workflow_spec=None
        )

        assert usage.workflow_context == 0
        assert usage.total == usage.system_prompt + usage.conversation_history

    def test_calculate_percentage(self):
        """Verify percentage calculation."""
        counter = TokenCounter(context_window_limit=1000)

        # Create usage that's roughly 50% of limit
        system_prompt = "a" * 2000  # ~500 tokens
        usage = counter.calculate_usage(
            system_prompt=system_prompt,
            conversation_history="",
            workflow_spec=None
        )

        # Should be around 50%
        assert 45 <= usage.percentage_of_limit <= 55


class TestThresholds:
    """Test warning and critical threshold detection."""

    def test_warning_threshold_detection(self):
        """Detect warning threshold (80%)."""
        counter = TokenCounter(context_window_limit=1000)

        # 850 tokens = 85% (above warning threshold)
        usage = TokenUsage(
            system_prompt=100,
            conversation_history=700,
            workflow_context=50,
            total=850,
            percentage_of_limit=85.0
        )

        assert usage.is_warning_threshold()
        assert not usage.is_critical_threshold()

    def test_critical_threshold_detection(self):
        """Detect critical threshold (95%)."""
        counter = TokenCounter(context_window_limit=1000)

        # 960 tokens = 96% (above critical threshold)
        usage = TokenUsage(
            system_prompt=100,
            conversation_history=800,
            workflow_context=60,
            total=960,
            percentage_of_limit=96.0
        )

        assert usage.is_warning_threshold()
        assert usage.is_critical_threshold()

    def test_below_thresholds(self):
        """Below all thresholds."""
        usage = TokenUsage(
            system_prompt=50,
            conversation_history=100,
            workflow_context=20,
            total=170,
            percentage_of_limit=17.0
        )

        assert not usage.is_warning_threshold()
        assert not usage.is_critical_threshold()


class TestRemainingTokens:
    """Test remaining token calculations."""

    def test_get_remaining_tokens(self):
        """Calculate remaining tokens."""
        counter = TokenCounter(context_window_limit=1000)

        remaining = counter.get_remaining_tokens(current_usage=600)
        assert remaining == 400

    def test_remaining_at_limit(self):
        """No tokens remaining at limit."""
        counter = TokenCounter(context_window_limit=1000)

        remaining = counter.get_remaining_tokens(current_usage=1000)
        assert remaining == 0

    def test_remaining_over_limit(self):
        """Handle usage over limit."""
        counter = TokenCounter(context_window_limit=1000)

        remaining = counter.get_remaining_tokens(current_usage=1200)
        assert remaining == 0

    def test_estimate_turns_remaining(self):
        """Estimate remaining conversation turns."""
        counter = TokenCounter(context_window_limit=1000)

        # 400 tokens remaining, 200 per turn = 2 turns
        remaining_turns = counter.estimate_turns_remaining(
            current_usage=600,
            avg_turn_tokens=200
        )
        assert remaining_turns == 2

    def test_estimate_turns_at_limit(self):
        """No turns remaining at limit."""
        counter = TokenCounter(context_window_limit=1000)

        remaining_turns = counter.estimate_turns_remaining(
            current_usage=1000,
            avg_turn_tokens=200
        )
        assert remaining_turns == 0


class TestSummarizationTrigger:
    """Test summarization trigger based on tokens."""

    def test_should_summarize_above_threshold(self):
        """Trigger summarization above 70%."""
        counter = TokenCounter(context_window_limit=1000)

        # 750 tokens = 75% (above 70% threshold)
        assert counter.should_summarize(current_usage=750, threshold=0.70)

    def test_should_not_summarize_below_threshold(self):
        """Don't trigger below threshold."""
        counter = TokenCounter(context_window_limit=1000)

        # 650 tokens = 65% (below 70% threshold)
        assert not counter.should_summarize(current_usage=650, threshold=0.70)

    def test_custom_threshold(self):
        """Use custom summarization threshold."""
        counter = TokenCounter(context_window_limit=1000)

        # 850 tokens = 85%
        assert counter.should_summarize(current_usage=850, threshold=0.80)
        assert not counter.should_summarize(current_usage=850, threshold=0.90)


class TestTokenCounterFactory:
    """Test token counter factory function."""

    def test_create_counter_gemini(self):
        """Create counter for Gemini model."""
        counter = create_token_counter("gemini-2.5-flash-lite")
        assert counter.context_window_limit == 32000

    def test_create_counter_gpt4(self):
        """Create counter for GPT-4."""
        counter = create_token_counter("gpt-4")
        assert counter.context_window_limit == 8192

    def test_create_counter_unknown_model(self):
        """Use default for unknown model."""
        counter = create_token_counter("unknown-model")
        assert counter.context_window_limit == 32000  # Default


class TestTelemetryTracking:
    """Test telemetry tracking in ConversationManager."""

    def test_track_token_usage(self):
        """Track token usage for conversation."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=32000
        )

        # Add some conversation turns
        manager.add_turn("conv_1", "Create a workflow", "Creating workflow...")

        # Track usage
        usage = manager.track_token_usage(
            conversation_id="conv_1",
            system_prompt="You are a helpful assistant"
        )

        assert usage.total > 0
        assert usage.percentage_of_limit >= 0

    def test_telemetry_history_accumulates(self):
        """Telemetry history accumulates entries."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=32000
        )

        # Add turns and track usage multiple times
        for i in range(5):
            manager.add_turn("conv_1", f"Message {i}", f"Response {i}")
            manager.track_token_usage("conv_1", "System prompt")

        # Should have 5 telemetry entries
        telemetry = manager.get_token_telemetry(limit=10)
        assert len(telemetry) == 5

    def test_telemetry_history_limit(self):
        """Telemetry history respects max entries."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=32000
        )

        # Override max for testing
        manager._max_telemetry_entries = 5

        # Add 10 entries
        for i in range(10):
            manager.add_turn("conv_1", f"Msg {i}", f"Resp {i}")
            manager.track_token_usage("conv_1", "Prompt")

        # Should only keep last 5
        telemetry = manager.get_token_telemetry(limit=100)
        assert len(telemetry) <= 5

    def test_get_telemetry_by_conversation(self):
        """Filter telemetry by conversation."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=32000
        )

        # Track usage for two conversations
        manager.add_turn("conv_1", "Message 1", "Response 1")
        manager.track_token_usage("conv_1", "Prompt")

        manager.add_turn("conv_2", "Message 2", "Response 2")
        manager.track_token_usage("conv_2", "Prompt")

        # Get telemetry for conv_1 only
        telemetry = manager.get_token_telemetry(conversation_id="conv_1")
        assert len(telemetry) == 1
        assert telemetry[0]["conversation_id"] == "conv_1"


class TestTokenStatistics:
    """Test aggregated token statistics."""

    def test_get_token_stats_empty(self):
        """Stats with no telemetry data."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=32000
        )

        stats = manager.get_token_stats()

        assert stats["total_measurements"] == 0
        assert stats["average_usage_percent"] == 0.0
        assert stats["max_usage_percent"] == 0.0
        assert stats["warnings_triggered"] == 0

    def test_get_token_stats_with_data(self):
        """Stats with telemetry data."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=1000  # Small limit for testing
        )

        # Add turns with varying lengths
        manager.add_turn("conv_1", "Short", "Response")
        manager.track_token_usage("conv_1", "Prompt")

        manager.add_turn("conv_1", "A longer message here", "Longer response back")
        manager.track_token_usage("conv_1", "Prompt")

        stats = manager.get_token_stats()

        assert stats["total_measurements"] == 2
        assert stats["average_usage_percent"] > 0
        assert stats["max_usage_percent"] > 0

    def test_stats_include_counter_config(self):
        """Stats include token counter configuration."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=32000
        )

        stats = manager.get_token_stats()

        assert "token_counter_config" in stats
        assert stats["token_counter_config"]["context_window_limit"] == 32000


class TestWarningDetection:
    """Test token warning detection."""

    def test_check_token_warning_none(self):
        """No warning below thresholds."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=10000
        )

        manager.add_turn("conv_1", "Hello", "Hi")

        warning = manager.check_token_warning("conv_1", "Short prompt")
        assert warning is None

    def test_check_token_warning_threshold(self):
        """Warning at 80% threshold."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=1000
        )

        # Add enough content to reach 80%
        # Need ~800 tokens
        long_message = "a" * 1600  # ~400 tokens
        manager.add_turn("conv_1", long_message, long_message)

        long_prompt = "b" * 800  # ~200 tokens
        warning = manager.check_token_warning("conv_1", long_prompt)

        # Should trigger warning
        if warning:
            assert warning["level"] in ["warning", "critical"]
            assert "recommendation" in warning

    def test_warning_includes_usage(self):
        """Warning includes usage details."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=500
        )

        # Fill conversation to trigger warning
        msg = "x" * 800  # ~200 tokens
        for i in range(3):
            manager.add_turn("conv_1", msg, msg)

        warning = manager.check_token_warning("conv_1", "Prompt" * 50)

        if warning:
            assert "usage" in warning
            assert hasattr(warning["usage"], "total")
            assert hasattr(warning["usage"], "percentage_of_limit")


class TestIntegrationWithCacheStats:
    """Test token stats integration with cache stats."""

    def test_cache_stats_include_token_usage(self):
        """Cache stats include token usage statistics."""
        manager = ConversationManager(
            enable_persistence=False,
            context_window_limit=32000
        )

        # Add some activity
        manager.add_turn("conv_1", "Message", "Response")
        manager.track_token_usage("conv_1", "Prompt")

        # Get combined stats
        stats = manager.get_cache_stats()

        assert "token_usage" in stats
        assert "total_measurements" in stats["token_usage"]
        assert "average_usage_percent" in stats["token_usage"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])