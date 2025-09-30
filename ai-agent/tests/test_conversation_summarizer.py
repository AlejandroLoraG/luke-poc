"""
Tests for ConversationSummarizer progressive summarization.

Tests cover:
- Threshold detection (70% trigger point)
- Early and recent turn preservation
- Simple fallback summarization with topic extraction
- LLM-based summarization (with mock)
- Integration with ConversationManager
- Cache management
- Statistics reporting
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.conversation_summarizer import ConversationSummarizer, create_llm_summarizer
from core.models import ConversationTurn
from core.conversation_manager import ConversationManager


class TestThresholdDetection:
    """Test summarization threshold detection."""

    def test_below_threshold(self):
        """No summarization when below 70% threshold."""
        summarizer = ConversationSummarizer(max_length=15, summary_threshold=0.70)

        # 70% of 15 = 10.5, so threshold is 10 turns
        assert not summarizer.should_summarize(9)

    def test_at_threshold(self):
        """Summarization triggers at exactly 70% threshold."""
        summarizer = ConversationSummarizer(max_length=15, summary_threshold=0.70)

        # 70% of 15 = 10.5, rounded to 10
        # Should trigger at 10 turns
        assert summarizer.should_summarize(10)

    def test_above_threshold(self):
        """Summarization triggers when above threshold."""
        summarizer = ConversationSummarizer(max_length=15, summary_threshold=0.70)

        assert summarizer.should_summarize(11)
        assert summarizer.should_summarize(15)
        assert summarizer.should_summarize(20)

    def test_custom_threshold(self):
        """Custom threshold values work correctly."""
        summarizer = ConversationSummarizer(max_length=20, summary_threshold=0.80)

        # 80% of 20 = 16
        assert not summarizer.should_summarize(15)
        assert summarizer.should_summarize(16)
        assert summarizer.should_summarize(20)


class TestTurnPreservation:
    """Test preservation of early and recent turns."""

    def test_preserve_early_turns(self):
        """Early turns are preserved unchanged."""
        summarizer = ConversationSummarizer(
            max_length=15,
            summary_threshold=0.70,
            preserve_early=2,
            preserve_recent=5
        )

        # Create 12 turns (above threshold)
        turns = [
            ConversationTurn(
                user_message=f"User message {i}",
                agent_response=f"Agent response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        summary, remaining_turns = summarizer.summarize_conversation(
            "conv_123",
            turns,
            llm_summarize_func=None
        )

        # Should preserve recent 5 turns
        assert len(remaining_turns) == 5
        assert remaining_turns[0].user_message == "User message 7"
        assert remaining_turns[-1].user_message == "User message 11"

        # Summary should mention early turns
        assert "User message 0" in summary
        assert "User message 1" in summary

    def test_preserve_recent_turns(self):
        """Recent turns are kept unsummarized."""
        summarizer = ConversationSummarizer(
            max_length=15,
            preserve_recent=5
        )

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        summary, remaining_turns = summarizer.summarize_conversation(
            "conv_123",
            turns
        )

        # Recent 5 turns should be returned
        assert len(remaining_turns) == 5
        for i, turn in enumerate(remaining_turns, start=7):
            assert f"Message {i}" in turn.user_message

    def test_no_middle_segment(self):
        """Handle case where early + recent covers all turns."""
        summarizer = ConversationSummarizer(
            max_length=15,
            preserve_early=5,
            preserve_recent=5
        )

        # Only 10 turns - exactly early + recent
        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(10)
        ]

        summary, remaining_turns = summarizer.summarize_conversation(
            "conv_123",
            turns
        )

        # Should still work, with minimal middle segment
        assert len(remaining_turns) == 5
        assert summary  # Summary should exist


class TestSimpleSummarization:
    """Test fallback simple summarization."""

    def test_simple_summarize_workflow_topics(self):
        """Extract workflow-related topics from turns."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message="I need to create a new approval workflow",
                agent_response="I'll help you create an approval workflow",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            ),
            ConversationTurn(
                user_message="Can you modify the states?",
                agent_response="Yes, I'll modify the workflow states",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            ),
            ConversationTurn(
                user_message="Please explain how this works",
                agent_response="Let me explain the workflow process",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
        ]

        summary = summarizer._simple_summarize(turns)

        assert "Discussed 3 topics" in summary
        assert "Workflow creation" in summary or "creation" in summary.lower()

    def test_topic_extraction(self):
        """Topic extraction identifies key patterns."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message="Create a new workflow",
                agent_response="Creating workflow...",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            ),
            ConversationTurn(
                user_message="Modify this workflow",
                agent_response="Modifying...",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
        ]

        topics = summarizer._extract_topics(turns)

        assert len(topics) > 0
        # Should detect creation and modification intents

    def test_topic_deduplication(self):
        """Duplicate topics are removed."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message="Create a workflow",
                agent_response="Creating...",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            ),
            ConversationTurn(
                user_message="Create another workflow",
                agent_response="Creating...",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
        ]

        topics = summarizer._extract_topics(turns)

        # Should deduplicate "Workflow creation discussion"
        unique_topics = list(set(topics))
        assert len(topics) == len(unique_topics)

    def test_empty_turns_handling(self):
        """Handle empty turn list gracefully."""
        summarizer = ConversationSummarizer()

        summary = summarizer._simple_summarize([])

        assert summary == "No conversation history"


class TestFullSummarization:
    """Test complete summarization flow."""

    def test_summarize_with_fallback(self):
        """Summarize conversation using simple fallback."""
        summarizer = ConversationSummarizer(
            max_length=15,
            summary_threshold=0.70,
            preserve_early=2,
            preserve_recent=5
        )

        turns = [
            ConversationTurn(
                user_message=f"Create workflow {i}",
                agent_response=f"Creating workflow {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        summary, remaining_turns = summarizer.summarize_conversation(
            "conv_123",
            turns,
            llm_summarize_func=None  # Force fallback
        )

        # Check structure
        assert "[Early conversation context:]" in summary
        assert "[Summary of" in summary
        assert "[Recent conversation:]" in summary

        # Check turn preservation
        assert len(remaining_turns) == 5

    def test_no_summarization_below_threshold(self):
        """No summarization when below threshold."""
        summarizer = ConversationSummarizer(max_length=15, summary_threshold=0.70)

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(5)  # Only 5 turns, below threshold
        ]

        summary, remaining_turns = summarizer.summarize_conversation(
            "conv_123",
            turns
        )

        # Should return empty summary and all turns
        assert summary == ""
        assert len(remaining_turns) == 5

    def test_format_turns(self):
        """Format turns as conversation string."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message="Hello",
                agent_response="Hi there",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            ),
            ConversationTurn(
                user_message="How are you?",
                agent_response="I'm good",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
        ]

        formatted = summarizer._format_turns(turns)

        assert "User: Hello" in formatted
        assert "Agent: Hi there" in formatted
        assert "User: How are you?" in formatted
        assert "Agent: I'm good" in formatted


class TestLLMSummarization:
    """Test LLM-based summarization with mocks."""

    def test_summarize_with_llm_function(self):
        """Use LLM summarization when provided."""
        summarizer = ConversationSummarizer(
            max_length=15,
            preserve_early=2,
            preserve_recent=5
        )

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        # Mock LLM function
        def mock_llm_summarize(middle_turns):
            return f"Discussed {len(middle_turns)} workflow topics including task management and approvals"

        summary, remaining_turns = summarizer.summarize_conversation(
            "conv_123",
            turns,
            llm_summarize_func=mock_llm_summarize
        )

        # Check LLM summary is used
        assert "workflow topics" in summary
        assert "task management" in summary

    def test_llm_failure_fallback(self):
        """Fall back to simple summarization if LLM fails."""
        summarizer = ConversationSummarizer(max_length=15)

        turns = [
            ConversationTurn(
                user_message="Create workflow",
                agent_response="Creating...",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        # Mock failing LLM function
        def failing_llm(middle_turns):
            raise Exception("LLM API error")

        summary, remaining_turns = summarizer.summarize_conversation(
            "conv_123",
            turns,
            llm_summarize_func=failing_llm
        )

        # Should still get a summary via fallback
        assert summary
        assert len(remaining_turns) == 5

    def test_create_llm_summarizer_function(self):
        """Test LLM summarizer factory function."""
        # Create mock model
        mock_model = Mock()

        # Create summarizer function
        summarize_func = create_llm_summarizer(mock_model)

        turns = [
            ConversationTurn(
                user_message="Test message",
                agent_response="Test response",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
        ]

        # Should return a summary (placeholder in current implementation)
        result = summarize_func(turns)
        assert isinstance(result, str)
        assert len(result) > 0


class TestCacheManagement:
    """Test summary caching."""

    def test_cache_summary(self):
        """Summaries are cached for reuse."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        # First summarization
        summary1, _ = summarizer.summarize_conversation("conv_123", turns)

        # Should be cached
        cached = summarizer.get_cached_summary("conv_123")
        assert cached is not None

    def test_get_cached_summary(self):
        """Retrieve cached summary."""
        summarizer = ConversationSummarizer()

        # No cache yet
        assert summarizer.get_cached_summary("conv_123") is None

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        # Create summary
        summarizer.summarize_conversation("conv_123", turns)

        # Should be cached now
        cached = summarizer.get_cached_summary("conv_123")
        assert cached is not None

    def test_clear_cache_specific(self):
        """Clear specific conversation cache."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        # Create summaries for two conversations
        summarizer.summarize_conversation("conv_1", turns)
        summarizer.summarize_conversation("conv_2", turns)

        # Clear one
        summarizer.clear_cache("conv_1")

        assert summarizer.get_cached_summary("conv_1") is None
        assert summarizer.get_cached_summary("conv_2") is not None

    def test_clear_cache_all(self):
        """Clear all cached summaries."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        # Create multiple summaries
        summarizer.summarize_conversation("conv_1", turns)
        summarizer.summarize_conversation("conv_2", turns)

        # Clear all
        summarizer.clear_cache()

        assert summarizer.get_cached_summary("conv_1") is None
        assert summarizer.get_cached_summary("conv_2") is None


class TestStatistics:
    """Test statistics reporting."""

    def test_get_stats(self):
        """Get summarizer statistics."""
        summarizer = ConversationSummarizer(
            max_length=15,
            summary_threshold=0.70,
            preserve_recent=5,
            preserve_early=2
        )

        stats = summarizer.get_stats()

        assert stats["max_length"] == 15
        assert stats["summary_threshold"] == 0.70
        assert stats["threshold_turns"] == 10  # 70% of 15
        assert stats["preserve_recent"] == 5
        assert stats["preserve_early"] == 2
        assert stats["cached_summaries"] == 0

    def test_stats_with_cached_summaries(self):
        """Stats reflect cached summary count."""
        summarizer = ConversationSummarizer()

        turns = [
            ConversationTurn(
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
                timestamp=datetime.now(),
                mcp_tools_used=[]
            )
            for i in range(12)
        ]

        # Create summaries
        summarizer.summarize_conversation("conv_1", turns)
        summarizer.summarize_conversation("conv_2", turns)

        stats = summarizer.get_stats()
        assert stats["cached_summaries"] == 2


class TestIntegrationWithManager:
    """Test integration with ConversationManager."""

    def test_manager_with_summarization_enabled(self):
        """ConversationManager integrates summarizer."""
        manager = ConversationManager(
            max_length=15,
            enable_persistence=False,
            enable_summarization=True,
            summary_threshold=0.70
        )

        assert manager.enable_summarization is True
        assert manager.summarizer is not None

    def test_manager_with_summarization_disabled(self):
        """ConversationManager works without summarizer."""
        manager = ConversationManager(
            max_length=15,
            enable_persistence=False,
            enable_summarization=False
        )

        assert manager.enable_summarization is False
        assert manager.summarizer is None

    def test_manager_applies_summarization(self):
        """Manager applies summarization to context string."""
        manager = ConversationManager(
            max_length=15,
            enable_persistence=False,
            enable_summarization=True,
            summary_threshold=0.70,
            preserve_early=2,
            preserve_recent=3
        )

        # Add 12 turns (above threshold)
        for i in range(12):
            manager.add_turn(
                "conv_123",
                f"User message {i}",
                f"Agent response {i}",
                []
            )

        # Get context string - should be summarized
        context = manager.get_context_string("conv_123")

        # Should contain summary markers
        assert "[Early conversation context:]" in context
        assert "[Summary of" in context
        assert "[Recent conversation:]" in context

    def test_manager_stats_include_summarization(self):
        """Manager stats include summarization info."""
        manager = ConversationManager(
            enable_persistence=False,
            enable_summarization=True
        )

        stats = manager.get_cache_stats()

        assert "summarization" in stats
        # When enabled, stats should contain summarizer metrics
        assert "max_length" in stats["summarization"]
        assert "summary_threshold" in stats["summarization"]

    def test_manager_no_summarization_below_threshold(self):
        """Manager doesn't summarize below threshold."""
        manager = ConversationManager(
            max_length=15,
            enable_persistence=False,
            enable_summarization=True,
            summary_threshold=0.70
        )

        # Add only 5 turns (below threshold)
        for i in range(5):
            manager.add_turn(
                "conv_123",
                f"User message {i}",
                f"Agent response {i}",
                []
            )

        context = manager.get_context_string("conv_123")

        # Should NOT contain summary markers
        assert "[Early conversation context:]" not in context
        assert "[Summary of" not in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])