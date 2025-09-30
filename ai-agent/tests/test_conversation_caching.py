"""
Tests for ConversationManager caching functionality.

Tests cover:
- Context string caching with TTL validation
- Workflow specification caching
- Cache statistics and monitoring
- Performance benchmarks
"""

import pytest
import time
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.conversation_manager import ConversationManager, CachedContext, CachedWorkflow


class TestContextStringCaching:
    """Test context string caching functionality."""

    def test_cache_miss_on_first_access(self):
        """First access should be a cache miss."""
        manager = ConversationManager()
        conv_id = "test_conv_1"

        # Add some turns
        manager.add_turn(conv_id, "Hello", "Hi there", [])
        manager.add_turn(conv_id, "How are you?", "I'm good", [])

        # First access - should be cache miss
        context = manager.get_context_string(conv_id)
        stats = manager.get_cache_stats()

        assert context != ""
        assert stats["context_cache"]["cache_misses"] == 1
        assert stats["context_cache"]["cache_hits"] == 0

    def test_cache_hit_on_subsequent_access(self):
        """Subsequent access should be a cache hit."""
        manager = ConversationManager()
        conv_id = "test_conv_2"

        manager.add_turn(conv_id, "Hello", "Hi", [])

        # First access - cache miss
        context1 = manager.get_context_string(conv_id)

        # Second access - should be cache hit
        context2 = manager.get_context_string(conv_id)

        stats = manager.get_cache_stats()

        assert context1 == context2
        assert stats["context_cache"]["cache_hits"] == 1
        assert stats["context_cache"]["cache_misses"] == 1

    def test_cache_invalidation_on_add_turn(self):
        """Adding a turn should invalidate the cache."""
        manager = ConversationManager()
        conv_id = "test_conv_3"

        manager.add_turn(conv_id, "First", "Response 1", [])
        context1 = manager.get_context_string(conv_id)  # Cache miss

        # Add another turn - should invalidate cache
        manager.add_turn(conv_id, "Second", "Response 2", [])
        context2 = manager.get_context_string(conv_id)  # Cache miss again

        stats = manager.get_cache_stats()

        assert context1 != context2
        assert "Second" in context2
        assert stats["context_cache"]["cache_misses"] == 2
        assert stats["context_cache"]["cache_hits"] == 0

    def test_cache_invalidation_on_clear_conversation(self):
        """Clearing conversation should invalidate cache."""
        manager = ConversationManager()
        conv_id = "test_conv_4"

        manager.add_turn(conv_id, "Hello", "Hi", [])
        manager.get_context_string(conv_id)  # Cache the context

        # Clear conversation
        manager.clear_conversation(conv_id)

        # Check cache is empty for this conversation
        context = manager.get_context_string(conv_id)
        assert context == ""

    def test_cache_ttl_expiration(self):
        """Cache should expire after TTL."""
        manager = ConversationManager(cache_ttl=0.1)  # 100ms TTL
        conv_id = "test_conv_5"

        manager.add_turn(conv_id, "Hello", "Hi", [])

        # First access - cache miss
        context1 = manager.get_context_string(conv_id)

        # Wait for TTL to expire
        time.sleep(0.2)

        # Access again - should be cache miss due to TTL expiration
        context2 = manager.get_context_string(conv_id)

        stats = manager.get_cache_stats()

        assert context1 == context2
        assert stats["context_cache"]["cache_misses"] == 2
        assert stats["context_cache"]["cache_hits"] == 0

    def test_cache_with_multiple_conversations(self):
        """Cache should work independently for multiple conversations."""
        manager = ConversationManager()

        # Create two conversations
        manager.add_turn("conv_a", "Hello A", "Hi A", [])
        manager.add_turn("conv_b", "Hello B", "Hi B", [])

        # Access both - should be cache misses
        context_a1 = manager.get_context_string("conv_a")
        context_b1 = manager.get_context_string("conv_b")

        # Access again - should be cache hits
        context_a2 = manager.get_context_string("conv_a")
        context_b2 = manager.get_context_string("conv_b")

        stats = manager.get_cache_stats()

        assert context_a1 == context_a2
        assert context_b1 == context_b2
        assert "Hello A" in context_a1
        assert "Hello B" in context_b1
        assert stats["context_cache"]["cache_hits"] == 2
        assert stats["context_cache"]["cache_misses"] == 2
        assert stats["context_cache"]["cached_conversations"] == 2


class TestWorkflowSpecCaching:
    """Test workflow specification caching."""

    def test_workflow_cache_miss_on_first_access(self):
        """First workflow access should be a cache miss."""
        manager = ConversationManager()
        workflow_id = "wf_test_1"

        result = manager.get_workflow_cached(workflow_id)
        stats = manager.get_cache_stats()

        assert result is None
        assert stats["workflow_cache"]["cache_misses"] == 1
        assert stats["workflow_cache"]["cache_hits"] == 0

    def test_workflow_cache_hit_after_caching(self):
        """Cached workflow should return cache hit."""
        manager = ConversationManager()
        workflow_id = "wf_test_2"
        workflow_spec = {
            "specId": workflow_id,
            "name": "Test Workflow",
            "states": [{"slug": "initial", "name": "Initial"}]
        }

        # Cache the workflow
        manager.cache_workflow(workflow_id, workflow_spec)

        # Access should be cache hit
        result = manager.get_workflow_cached(workflow_id)
        stats = manager.get_cache_stats()

        assert result is not None
        assert result["specId"] == workflow_id
        assert stats["workflow_cache"]["cache_hits"] == 1
        assert stats["workflow_cache"]["cache_misses"] == 0

    def test_workflow_cache_ttl_expiration(self):
        """Workflow cache should expire after TTL."""
        manager = ConversationManager(cache_ttl=0.1)  # 100ms TTL
        workflow_id = "wf_test_3"
        workflow_spec = {"specId": workflow_id, "name": "Test"}

        # Cache the workflow
        manager.cache_workflow(workflow_id, workflow_spec)

        # First access - cache hit
        result1 = manager.get_workflow_cached(workflow_id)
        assert result1 is not None

        # Wait for TTL expiration
        time.sleep(0.2)

        # Second access - cache miss due to expiration
        result2 = manager.get_workflow_cached(workflow_id)
        stats = manager.get_cache_stats()

        assert result2 is None
        assert stats["workflow_cache"]["cache_hits"] == 1
        assert stats["workflow_cache"]["cache_misses"] == 1

    def test_workflow_cache_invalidation(self):
        """Manual workflow cache invalidation should work."""
        manager = ConversationManager()
        workflow_id = "wf_test_4"
        workflow_spec = {"specId": workflow_id, "name": "Test"}

        # Cache the workflow
        manager.cache_workflow(workflow_id, workflow_spec)

        # Verify it's cached
        result1 = manager.get_workflow_cached(workflow_id)
        assert result1 is not None

        # Invalidate cache
        manager.invalidate_workflow_cache(workflow_id)

        # Should be cache miss now
        result2 = manager.get_workflow_cached(workflow_id)
        stats = manager.get_cache_stats()

        assert result2 is None
        assert stats["workflow_cache"]["cache_hits"] == 1
        assert stats["workflow_cache"]["cache_misses"] == 1

    def test_workflow_cache_clear_all(self):
        """Clearing all workflow cache should work."""
        manager = ConversationManager()

        # Cache multiple workflows
        for i in range(3):
            workflow_id = f"wf_test_{i}"
            workflow_spec = {"specId": workflow_id, "name": f"Test {i}"}
            manager.cache_workflow(workflow_id, workflow_spec)

        # Clear all caches
        manager.invalidate_workflow_cache()

        # All should be cache misses now
        for i in range(3):
            result = manager.get_workflow_cached(f"wf_test_{i}")
            assert result is None

        stats = manager.get_cache_stats()
        assert stats["workflow_cache"]["cached_workflows"] == 0


class TestCacheStatistics:
    """Test cache statistics and monitoring."""

    def test_cache_stats_initial_state(self):
        """Initial cache stats should be zero."""
        manager = ConversationManager()
        stats = manager.get_cache_stats()

        assert stats["context_cache"]["cache_hits"] == 0
        assert stats["context_cache"]["cache_misses"] == 0
        assert stats["context_cache"]["total_requests"] == 0
        assert stats["context_cache"]["hit_rate_percent"] == 0.0
        assert stats["context_cache"]["cached_conversations"] == 0

        assert stats["workflow_cache"]["cache_hits"] == 0
        assert stats["workflow_cache"]["cache_misses"] == 0
        assert stats["workflow_cache"]["total_requests"] == 0
        assert stats["workflow_cache"]["hit_rate_percent"] == 0.0
        assert stats["workflow_cache"]["cached_workflows"] == 0

    def test_cache_hit_rate_calculation(self):
        """Hit rate should be calculated correctly."""
        manager = ConversationManager()
        conv_id = "test_conv"

        manager.add_turn(conv_id, "Hello", "Hi", [])

        # 1 miss
        manager.get_context_string(conv_id)

        # 3 hits
        for _ in range(3):
            manager.get_context_string(conv_id)

        stats = manager.get_cache_stats()

        assert stats["context_cache"]["cache_hits"] == 3
        assert stats["context_cache"]["cache_misses"] == 1
        assert stats["context_cache"]["total_requests"] == 4
        assert stats["context_cache"]["hit_rate_percent"] == 75.0

    def test_reset_cache_stats(self):
        """Resetting cache stats should clear counters."""
        manager = ConversationManager()
        conv_id = "test_conv"

        manager.add_turn(conv_id, "Hello", "Hi", [])
        manager.get_context_string(conv_id)
        manager.get_context_string(conv_id)

        # Reset stats
        manager.reset_cache_stats()
        stats = manager.get_cache_stats()

        assert stats["context_cache"]["cache_hits"] == 0
        assert stats["context_cache"]["cache_misses"] == 0
        assert stats["workflow_cache"]["cache_hits"] == 0
        assert stats["workflow_cache"]["cache_misses"] == 0

    def test_clear_cache_method(self):
        """Clear cache should remove cached contexts."""
        manager = ConversationManager()

        # Create multiple conversations
        for i in range(3):
            conv_id = f"conv_{i}"
            manager.add_turn(conv_id, "Hello", "Hi", [])
            manager.get_context_string(conv_id)

        stats_before = manager.get_cache_stats()
        assert stats_before["context_cache"]["cached_conversations"] == 3

        # Clear specific conversation cache
        manager.clear_cache("conv_0")
        stats_after = manager.get_cache_stats()
        assert stats_after["context_cache"]["cached_conversations"] == 2

        # Clear all cache
        manager.clear_cache()
        stats_final = manager.get_cache_stats()
        assert stats_final["context_cache"]["cached_conversations"] == 0


class TestCachePerformance:
    """Performance benchmarks for caching."""

    def test_cache_performance_improvement(self):
        """Cache should provide performance improvement."""
        manager = ConversationManager()
        conv_id = "perf_test"

        # Create a conversation with many turns
        for i in range(50):
            manager.add_turn(conv_id, f"Message {i}", f"Response {i}", [])

        # Measure uncached access (first access)
        start_uncached = time.time()
        context1 = manager.get_context_string(conv_id)
        uncached_time = time.time() - start_uncached

        # Measure cached access (subsequent accesses)
        cached_times = []
        for _ in range(10):
            start_cached = time.time()
            context2 = manager.get_context_string(conv_id)
            cached_times.append(time.time() - start_cached)

        avg_cached_time = sum(cached_times) / len(cached_times)

        # Cache should be significantly faster
        # In practice, cache should be 50-100x faster for large contexts
        assert avg_cached_time < uncached_time
        assert context1 == context2

        stats = manager.get_cache_stats()
        assert stats["context_cache"]["cache_hits"] == 10
        assert stats["context_cache"]["hit_rate_percent"] > 90.0

    def test_cache_memory_efficiency(self):
        """Cache should efficiently handle multiple conversations."""
        manager = ConversationManager()

        # Create 100 conversations
        for i in range(100):
            conv_id = f"conv_{i}"
            manager.add_turn(conv_id, f"Message {i}", f"Response {i}", [])
            manager.get_context_string(conv_id)

        stats = manager.get_cache_stats()

        # All conversations should be cached
        assert stats["context_cache"]["cached_conversations"] == 100
        assert stats["context_cache"]["cache_misses"] == 100

        # Access half of them again
        for i in range(50):
            manager.get_context_string(f"conv_{i}")

        stats = manager.get_cache_stats()
        assert stats["context_cache"]["cache_hits"] == 50
        assert stats["context_cache"]["hit_rate_percent"] == pytest.approx(33.33, rel=0.1)


class TestCachedContextDataclass:
    """Test CachedContext dataclass functionality."""

    def test_cached_context_is_valid_fresh(self):
        """CachedContext should be valid when fresh and current."""
        cached = CachedContext(
            context_string="test context",
            turn_count=5,
            cached_at=time.time()
        )

        assert cached.is_valid(current_turn_count=5, ttl=300.0)

    def test_cached_context_invalid_stale(self):
        """CachedContext should be invalid when stale."""
        cached = CachedContext(
            context_string="test context",
            turn_count=5,
            cached_at=time.time() - 400  # 400 seconds ago
        )

        assert not cached.is_valid(current_turn_count=5, ttl=300.0)

    def test_cached_context_invalid_outdated_turn_count(self):
        """CachedContext should be invalid when turn count changed."""
        cached = CachedContext(
            context_string="test context",
            turn_count=5,
            cached_at=time.time()
        )

        assert not cached.is_valid(current_turn_count=6, ttl=300.0)


class TestCachedWorkflowDataclass:
    """Test CachedWorkflow dataclass functionality."""

    def test_cached_workflow_is_valid_fresh(self):
        """CachedWorkflow should be valid when fresh."""
        cached = CachedWorkflow(
            workflow_spec={"specId": "test"},
            cached_at=time.time()
        )

        assert cached.is_valid(ttl=300.0)

    def test_cached_workflow_invalid_stale(self):
        """CachedWorkflow should be invalid when stale."""
        cached = CachedWorkflow(
            workflow_spec={"specId": "test"},
            cached_at=time.time() - 400  # 400 seconds ago
        )

        assert not cached.is_valid(ttl=300.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])