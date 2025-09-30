import time
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass

from .models import ConversationTurn
from .conversation_persistence import ConversationPersistence
from .workflow_memory import WorkflowMemory
from .conversation_summarizer import ConversationSummarizer
from .token_counter import TokenCounter, TokenUsage


@dataclass
class CachedContext:
    """Cached conversation context string with validation."""
    context_string: str
    turn_count: int
    cached_at: float

    def is_valid(self, current_turn_count: int, ttl: float = 300.0) -> bool:
        """
        Check if cache is still valid.

        Args:
            current_turn_count: Current number of turns in conversation
            ttl: Time-to-live in seconds

        Returns:
            True if cache is fresh and current, False otherwise
        """
        is_fresh = (time.time() - self.cached_at) < ttl
        is_current = self.turn_count == current_turn_count
        return is_fresh and is_current


@dataclass
class CachedWorkflow:
    """Cached workflow specification with TTL validation."""
    workflow_spec: Dict[str, Any]
    cached_at: float

    def is_valid(self, ttl: float = 300.0) -> bool:
        """
        Check if workflow cache is still valid.

        Args:
            ttl: Time-to-live in seconds

        Returns:
            True if cache is fresh, False otherwise
        """
        return (time.time() - self.cached_at) < ttl


class ConversationManager:
    def __init__(
        self,
        max_length: int = 15,
        cache_ttl: float = 300.0,
        enable_persistence: bool = True,
        storage_dir: str = "storage/conversations",
        enable_summarization: bool = True,
        summary_threshold: float = 0.70,
        preserve_recent: int = 5,
        preserve_early: int = 2,
        context_window_limit: int = 32000
    ):
        """
        Initialize conversation manager with caching and persistence.

        Args:
            max_length: Maximum conversation turns to retain
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            enable_persistence: Enable file-based persistence
            storage_dir: Directory for conversation storage
            enable_summarization: Enable progressive summarization
            summary_threshold: Trigger summarization at this percentage (0.0-1.0)
            preserve_recent: Number of recent turns to keep unsummarized
            preserve_early: Number of early turns to keep for context
            context_window_limit: Model context window limit in tokens
        """
        self.max_length = max_length
        self.cache_ttl = cache_ttl
        self.enable_persistence = enable_persistence
        self.enable_summarization = enable_summarization
        self.conversations: Dict[str, List[ConversationTurn]] = {}

        # Track conversation creation times for persistence
        self._conversation_created_at: Dict[str, datetime] = {}

        # Workflow memory for each conversation
        self._workflow_memories: Dict[str, WorkflowMemory] = {}

        # Context string cache
        self._context_cache: Dict[str, CachedContext] = {}

        # Workflow specification cache
        self._workflow_cache: Dict[str, CachedWorkflow] = {}

        # Cache statistics (for monitoring)
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._workflow_cache_hits: int = 0
        self._workflow_cache_misses: int = 0

        # Token usage telemetry
        self._token_usage_history: List[Dict[str, Any]] = []
        self._max_telemetry_entries: int = 100

        # Initialize persistence layer
        if enable_persistence:
            self.persistence = ConversationPersistence(storage_dir)
        else:
            self.persistence = None

        # Initialize summarization layer
        if enable_summarization:
            self.summarizer = ConversationSummarizer(
                max_length=max_length,
                summary_threshold=summary_threshold,
                preserve_recent=preserve_recent,
                preserve_early=preserve_early
            )
        else:
            self.summarizer = None

        # Initialize token counter
        self.token_counter = TokenCounter(context_window_limit=context_window_limit)

    def add_turn(
        self,
        conversation_id: str,
        user_message: str,
        agent_response: str,
        mcp_tools_used: List[str] = None
    ) -> int:
        """
        Add a conversation turn, invalidate cache, and persist to disk.
        """
        if mcp_tools_used is None:
            mcp_tools_used = []

        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
            self._conversation_created_at[conversation_id] = datetime.now()

        turn = ConversationTurn(
            user_message=user_message,
            agent_response=agent_response,
            timestamp=datetime.now(),
            mcp_tools_used=mcp_tools_used
        )

        self.conversations[conversation_id].append(turn)

        # Trim conversation if it exceeds max length
        if len(self.conversations[conversation_id]) > self.max_length:
            self.conversations[conversation_id] = self.conversations[conversation_id][-self.max_length:]

        # Invalidate cache for this conversation
        if conversation_id in self._context_cache:
            del self._context_cache[conversation_id]

        # Persist to disk (graceful degradation on failure)
        if self.enable_persistence and self.persistence:
            created_at = self._conversation_created_at.get(conversation_id)
            self.persistence.save_conversation(
                conversation_id,
                self.conversations[conversation_id],
                created_at
            )

        return len(self.conversations[conversation_id])

    def get_conversation_history(self, conversation_id: str) -> List[ConversationTurn]:
        """
        Get conversation history with automatic loading from persistence.
        """
        # Return from memory if available
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]

        # Try to load from persistence
        if self.enable_persistence and self.persistence:
            turns = self.persistence.load_conversation(conversation_id)
            if turns:
                self.conversations[conversation_id] = turns
                # Set created_at from first turn timestamp
                if turns:
                    self._conversation_created_at[conversation_id] = turns[0].timestamp
                return turns

        return []

    def get_context_string(self, conversation_id: str) -> str:
        """
        Get context string for a conversation with caching and summarization.

        Returns cached context if valid, otherwise rebuilds with optional
        summarization and caches the result.
        """
        # Check cache first
        current_turn_count = self.get_conversation_count(conversation_id)

        if conversation_id in self._context_cache:
            cached = self._context_cache[conversation_id]
            if cached.is_valid(current_turn_count, self.cache_ttl):
                self._cache_hits += 1
                return cached.context_string

        # Cache miss - rebuild context
        self._cache_misses += 1

        history = self.get_conversation_history(conversation_id)
        if not history:
            return ""

        # Apply summarization if enabled and threshold reached
        summary_string = ""
        turns_to_format = history

        if self.enable_summarization and self.summarizer:
            if self.summarizer.should_summarize(len(history)):
                summary_string, turns_to_format = self.summarizer.summarize_conversation(
                    conversation_id,
                    history,
                    llm_summarize_func=None  # Use simple fallback for now
                )

        # Build context string
        context_parts = []

        # Add summary if available
        if summary_string:
            context_parts.append(summary_string)

        # Add unsummarized turns
        for turn in turns_to_format:
            context_parts.append(f"User: {turn.user_message}")
            context_parts.append(f"Agent: {turn.agent_response}")

        context_string = "\n\n".join(context_parts)

        # Update cache
        self._context_cache[conversation_id] = CachedContext(
            context_string=context_string,
            turn_count=current_turn_count,
            cached_at=time.time()
        )

        return context_string

    def get_conversation_count(self, conversation_id: str) -> int:
        return len(self.conversations.get(conversation_id, []))

    def clear_conversation(self, conversation_id: str):
        """Clear conversation history, cache, and persistent storage."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]

        if conversation_id in self._conversation_created_at:
            del self._conversation_created_at[conversation_id]

        # Invalidate cache for this conversation
        if conversation_id in self._context_cache:
            del self._context_cache[conversation_id]

        # Delete from persistence
        if self.enable_persistence and self.persistence:
            self.persistence.delete_conversation(conversation_id)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics and persistence info.

        Returns:
            Dictionary with cache metrics and persistence statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        total_workflow_requests = self._workflow_cache_hits + self._workflow_cache_misses
        workflow_hit_rate = (self._workflow_cache_hits / total_workflow_requests * 100) if total_workflow_requests > 0 else 0.0

        stats = {
            "context_cache": {
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "cached_conversations": len(self._context_cache)
            },
            "workflow_cache": {
                "cache_hits": self._workflow_cache_hits,
                "cache_misses": self._workflow_cache_misses,
                "total_requests": total_workflow_requests,
                "hit_rate_percent": round(workflow_hit_rate, 2),
                "cached_workflows": len(self._workflow_cache)
            }
        }

        # Add persistence stats if enabled
        if self.enable_persistence and self.persistence:
            stats["persistence"] = self.persistence.get_stats()
        else:
            stats["persistence"] = {"enabled": False}

        # Add summarization stats if enabled
        if self.enable_summarization and self.summarizer:
            stats["summarization"] = self.summarizer.get_stats()
        else:
            stats["summarization"] = {"enabled": False}

        # Add token usage stats
        stats["token_usage"] = self.get_token_stats()

        return stats

    def clear_cache(self, conversation_id: Optional[str] = None):
        """
        Clear context cache.

        Args:
            conversation_id: If provided, clear only this conversation's cache.
                           If None, clear entire cache.
        """
        if conversation_id:
            if conversation_id in self._context_cache:
                del self._context_cache[conversation_id]
        else:
            self._context_cache.clear()

    def reset_cache_stats(self):
        """Reset cache statistics counters."""
        self._cache_hits = 0
        self._cache_misses = 0
        self._workflow_cache_hits = 0
        self._workflow_cache_misses = 0

    def get_workflow_cached(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached workflow specification.

        Args:
            workflow_id: Workflow specification ID

        Returns:
            Cached workflow spec if valid, None otherwise
        """
        if workflow_id in self._workflow_cache:
            cached = self._workflow_cache[workflow_id]
            if cached.is_valid(self.cache_ttl):
                self._workflow_cache_hits += 1
                return cached.workflow_spec

        self._workflow_cache_misses += 1
        return None

    def cache_workflow(self, workflow_id: str, workflow_spec: Dict[str, Any]):
        """
        Cache a workflow specification.

        Args:
            workflow_id: Workflow specification ID
            workflow_spec: Complete workflow specification to cache
        """
        self._workflow_cache[workflow_id] = CachedWorkflow(
            workflow_spec=workflow_spec,
            cached_at=time.time()
        )

    def invalidate_workflow_cache(self, workflow_id: Optional[str] = None):
        """
        Invalidate workflow cache.

        Args:
            workflow_id: If provided, invalidate only this workflow.
                        If None, invalidate entire workflow cache.
        """
        if workflow_id:
            if workflow_id in self._workflow_cache:
                del self._workflow_cache[workflow_id]
        else:
            self._workflow_cache.clear()

    def get_workflow_memory(self, conversation_id: str) -> WorkflowMemory:
        """
        Get or create workflow memory for a conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            WorkflowMemory instance for this conversation
        """
        if conversation_id not in self._workflow_memories:
            self._workflow_memories[conversation_id] = WorkflowMemory()

        return self._workflow_memories[conversation_id]

    def track_workflow(
        self,
        conversation_id: str,
        spec_id: str,
        name: str,
        action: str = "discussed",
        aliases: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None
    ):
        """
        Track a workflow in conversation memory.

        Args:
            conversation_id: Unique conversation identifier
            spec_id: Workflow specification ID
            name: Business-friendly workflow name
            action: What happened (created, modified, discussed, viewed)
            aliases: Alternative names for search
            tags: Categorization tags
        """
        memory = self.get_workflow_memory(conversation_id)
        memory.add_workflow(spec_id, name, action, aliases, tags)

    def get_workflow_context(self, conversation_id: str, limit: int = 5) -> str:
        """
        Get formatted workflow context for conversation.

        Args:
            conversation_id: Unique conversation identifier
            limit: Maximum workflows to include

        Returns:
            Formatted workflow context string
        """
        memory = self.get_workflow_memory(conversation_id)
        return memory.format_for_context(limit)

    def track_token_usage(
        self,
        conversation_id: str,
        system_prompt: str,
        workflow_spec: Optional[Dict[str, Any]] = None
    ) -> TokenUsage:
        """
        Track token usage for a conversation and store telemetry.

        Args:
            conversation_id: Unique conversation identifier
            system_prompt: Current system prompt text
            workflow_spec: Optional workflow specification

        Returns:
            TokenUsage breakdown for this conversation
        """
        # Get conversation history
        context_string = self.get_context_string(conversation_id)

        # Calculate usage
        usage = self.token_counter.calculate_usage(
            system_prompt=system_prompt,
            conversation_history=context_string,
            workflow_spec=workflow_spec
        )

        # Store telemetry entry
        telemetry_entry = {
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "total_tokens": usage.total,
            "percentage": usage.percentage_of_limit,
            "system_prompt_tokens": usage.system_prompt,
            "conversation_tokens": usage.conversation_history,
            "workflow_tokens": usage.workflow_context,
            "turn_count": self.get_conversation_count(conversation_id),
            "warning_threshold_exceeded": usage.is_warning_threshold(),
            "critical_threshold_exceeded": usage.is_critical_threshold()
        }

        # Add to telemetry history (keep last N entries)
        self._token_usage_history.append(telemetry_entry)
        if len(self._token_usage_history) > self._max_telemetry_entries:
            self._token_usage_history.pop(0)

        return usage

    def get_token_telemetry(
        self,
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get token usage telemetry history.

        Args:
            conversation_id: Filter by conversation (None for all)
            limit: Maximum entries to return

        Returns:
            List of telemetry entries (most recent first)
        """
        # Filter by conversation if specified
        if conversation_id:
            filtered = [
                entry for entry in self._token_usage_history
                if entry["conversation_id"] == conversation_id
            ]
        else:
            filtered = self._token_usage_history

        # Return most recent entries
        return list(reversed(filtered[-limit:]))

    def get_token_stats(self) -> Dict[str, Any]:
        """
        Get aggregated token usage statistics.

        Returns:
            Dictionary with token usage metrics
        """
        if not self._token_usage_history:
            return {
                "total_measurements": 0,
                "average_usage_percent": 0.0,
                "max_usage_percent": 0.0,
                "warnings_triggered": 0,
                "critical_alerts_triggered": 0,
                "token_counter_config": self.token_counter.get_stats()
            }

        # Calculate statistics
        total = len(self._token_usage_history)
        percentages = [entry["percentage"] for entry in self._token_usage_history]
        warnings = sum(1 for entry in self._token_usage_history if entry["warning_threshold_exceeded"])
        criticals = sum(1 for entry in self._token_usage_history if entry["critical_threshold_exceeded"])

        return {
            "total_measurements": total,
            "average_usage_percent": round(sum(percentages) / total, 2) if total > 0 else 0.0,
            "max_usage_percent": round(max(percentages), 2) if percentages else 0.0,
            "min_usage_percent": round(min(percentages), 2) if percentages else 0.0,
            "warnings_triggered": warnings,
            "critical_alerts_triggered": criticals,
            "token_counter_config": self.token_counter.get_stats()
        }

    def check_token_warning(
        self,
        conversation_id: str,
        system_prompt: str,
        workflow_spec: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if token usage exceeds warning thresholds.

        Args:
            conversation_id: Unique conversation identifier
            system_prompt: Current system prompt text
            workflow_spec: Optional workflow specification

        Returns:
            Warning dict if threshold exceeded, None otherwise
        """
        usage = self.track_token_usage(conversation_id, system_prompt, workflow_spec)

        if usage.is_critical_threshold():
            return {
                "level": "critical",
                "message": f"Token usage at {usage.percentage_of_limit}% of limit (>95%)",
                "usage": usage,
                "recommendation": "Immediate summarization or conversation reset recommended"
            }
        elif usage.is_warning_threshold():
            return {
                "level": "warning",
                "message": f"Token usage at {usage.percentage_of_limit}% of limit (>80%)",
                "usage": usage,
                "recommendation": "Consider enabling summarization or managing conversation length"
            }

        return None