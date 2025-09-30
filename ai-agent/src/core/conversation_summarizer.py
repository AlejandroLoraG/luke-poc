"""
Progressive conversation summarization with semantic preservation.

Uses LLM-based summarization to maintain context while reducing token usage.
Triggers at 70% of max conversation length with graceful fallback.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import ConversationTurn


class ConversationSummarizer:
    """
    Progressive conversation summarizer using LLM for semantic preservation.

    Design principles:
    - Trigger at 70% threshold (configurable)
    - Preserve early context (first 2-3 turns)
    - Semantic summarization via LLM
    - Graceful fallback to simple truncation
    - Keep recent turns intact
    """

    def __init__(
        self,
        max_length: int = 15,
        summary_threshold: float = 0.70,
        preserve_recent: int = 5,
        preserve_early: int = 2
    ):
        """
        Initialize conversation summarizer.

        Args:
            max_length: Maximum conversation turns to retain
            summary_threshold: Trigger summarization at this percentage (0.0-1.0)
            preserve_recent: Number of recent turns to keep unsummarized
            preserve_early: Number of early turns to keep for context
        """
        self.max_length = max_length
        self.summary_threshold = summary_threshold
        self.preserve_recent = preserve_recent
        self.preserve_early = preserve_early

        # Cached summaries
        self._summaries: Dict[str, str] = {}

    def should_summarize(self, conversation_length: int) -> bool:
        """
        Check if conversation should be summarized.

        Args:
            conversation_length: Current number of turns

        Returns:
            True if summarization threshold reached
        """
        threshold_turns = int(self.max_length * self.summary_threshold)
        return conversation_length >= threshold_turns

    def summarize_conversation(
        self,
        conversation_id: str,
        turns: List[ConversationTurn],
        llm_summarize_func: Optional[callable] = None
    ) -> tuple[str, List[ConversationTurn]]:
        """
        Summarize conversation with semantic preservation.

        Args:
            conversation_id: Unique conversation identifier
            turns: Full conversation turns
            llm_summarize_func: Optional LLM function for semantic summarization

        Returns:
            Tuple of (summary_string, remaining_unsummarized_turns)
        """
        if not self.should_summarize(len(turns)):
            # No summarization needed
            return "", turns

        # Calculate split points
        early_cutoff = self.preserve_early
        recent_start = max(len(turns) - self.preserve_recent, early_cutoff)

        # Split conversation into segments
        early_turns = turns[:early_cutoff]
        middle_turns = turns[early_cutoff:recent_start]
        recent_turns = turns[recent_start:]

        # Generate summary for middle segment
        if llm_summarize_func and middle_turns:
            try:
                summary = llm_summarize_func(middle_turns)
            except Exception as e:
                print(f"LLM summarization failed: {e}, using fallback")
                summary = self._simple_summarize(middle_turns)
        else:
            summary = self._simple_summarize(middle_turns)

        # Cache the summary regardless of source
        if middle_turns:
            self._summaries[conversation_id] = summary

        # Format final summary with early context
        early_context = self._format_turns(early_turns)
        full_summary = f"""[Early conversation context:]
{early_context}

[Summary of {len(middle_turns)} middle turns:]
{summary}

[Recent conversation:]"""

        return full_summary, recent_turns

    def _simple_summarize(self, turns: List[ConversationTurn]) -> str:
        """
        Simple fallback summarization.

        Args:
            turns: Turns to summarize

        Returns:
            Basic summary string
        """
        if not turns:
            return "No conversation history"

        # Extract key information
        turn_count = len(turns)
        topics = self._extract_topics(turns)

        summary_parts = [
            f"Discussed {turn_count} topics including:"
        ]

        # Add topic bullets (max 3)
        for topic in topics[:3]:
            summary_parts.append(f"- {topic}")

        if len(topics) > 3:
            summary_parts.append(f"- And {len(topics) - 3} more topics...")

        return "\n".join(summary_parts)

    def _extract_topics(self, turns: List[ConversationTurn]) -> List[str]:
        """
        Extract key topics from conversation turns.

        Args:
            turns: Conversation turns

        Returns:
            List of identified topics
        """
        topics = []

        for turn in turns:
            # Simple keyword extraction from user messages
            message_lower = turn.user_message.lower()

            # Check for workflow-related keywords
            if "create" in message_lower or "new" in message_lower:
                topics.append("Workflow creation discussion")
            elif "modify" in message_lower or "change" in message_lower:
                topics.append("Workflow modification")
            elif "explain" in message_lower or "what is" in message_lower:
                topics.append("Workflow explanation")
            elif "workflow" in message_lower:
                topics.append("Workflow-related question")
            elif len(turn.user_message) > 10:
                # Generic topic for non-trivial messages
                topics.append(turn.user_message[:50] + "...")

        # Deduplicate while preserving order
        seen = set()
        unique_topics = []
        for topic in topics:
            if topic not in seen:
                seen.add(topic)
                unique_topics.append(topic)

        return unique_topics

    def _format_turns(self, turns: List[ConversationTurn]) -> str:
        """
        Format turns as conversation string.

        Args:
            turns: Turns to format

        Returns:
            Formatted conversation string
        """
        parts = []
        for turn in turns:
            parts.append(f"User: {turn.user_message}")
            parts.append(f"Agent: {turn.agent_response}")

        return "\n\n".join(parts)

    def get_cached_summary(self, conversation_id: str) -> Optional[str]:
        """
        Get cached summary for conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Cached summary or None
        """
        return self._summaries.get(conversation_id)

    def clear_cache(self, conversation_id: Optional[str] = None):
        """
        Clear summary cache.

        Args:
            conversation_id: If provided, clear only this conversation.
                           If None, clear all.
        """
        if conversation_id:
            self._summaries.pop(conversation_id, None)
        else:
            self._summaries.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get summarizer statistics.

        Returns:
            Dictionary with summarizer metrics
        """
        return {
            "max_length": self.max_length,
            "summary_threshold": self.summary_threshold,
            "threshold_turns": int(self.max_length * self.summary_threshold),
            "preserve_recent": self.preserve_recent,
            "preserve_early": self.preserve_early,
            "cached_summaries": len(self._summaries)
        }


def create_llm_summarizer(model: Any) -> callable:
    """
    Create LLM-based summarization function.

    Args:
        model: AI model instance for summarization

    Returns:
        Callable that takes turns and returns summary
    """
    def summarize_turns(turns: List[ConversationTurn]) -> str:
        """
        Summarize conversation turns using LLM.

        Args:
            turns: Conversation turns to summarize

        Returns:
            Semantic summary string
        """
        # Build context for LLM
        conversation_text = []
        for i, turn in enumerate(turns, 1):
            conversation_text.append(f"Turn {i}:")
            conversation_text.append(f"User: {turn.user_message}")
            conversation_text.append(f"Agent: {turn.agent_response}")
            conversation_text.append("")

        full_text = "\n".join(conversation_text)

        # Summarization prompt
        prompt = f"""Summarize this conversation in 2-3 sentences, focusing on:
- Key topics discussed
- Important decisions or outcomes
- Workflow operations performed

Conversation:
{full_text}

Concise summary:"""

        try:
            # Use model to generate summary
            # This is a placeholder - actual implementation depends on model API
            summary = f"Discussed workflow topics and performed operations (turns {1}-{len(turns)})"
            return summary
        except Exception as e:
            raise Exception(f"LLM summarization failed: {e}")

    return summarize_turns