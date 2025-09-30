import time
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from .conversation_persistence import ConversationPersistence


@dataclass
class ConversationTurn:
    user_message: str
    agent_response: str
    timestamp: datetime
    mcp_tools_used: List[str]


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
        storage_dir: str = "storage/conversations"
    ):
        """
        Initialize conversation manager with caching and persistence.

        Args:
            max_length: Maximum conversation turns to retain
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            enable_persistence: Enable file-based persistence
            storage_dir: Directory for conversation storage
        """
        self.max_length = max_length
        self.cache_ttl = cache_ttl
        self.enable_persistence = enable_persistence
        self.conversations: Dict[str, List[ConversationTurn]] = {}

        # Track conversation creation times for persistence
        self._conversation_created_at: Dict[str, datetime] = {}

        # Context string cache
        self._context_cache: Dict[str, CachedContext] = {}

        # Workflow specification cache
        self._workflow_cache: Dict[str, CachedWorkflow] = {}

        # Cache statistics (for monitoring)
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._workflow_cache_hits: int = 0
        self._workflow_cache_misses: int = 0

        # Initialize persistence layer
        if enable_persistence:
            self.persistence = ConversationPersistence(storage_dir)
        else:
            self.persistence = None

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
        Get context string for a conversation with caching.

        Returns cached context if valid, otherwise rebuilds and caches.
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

        context_parts = []
        for turn in history:
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