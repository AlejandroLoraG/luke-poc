"""
Token counting utility for context window management.

Uses approximation for PoC: 4 characters ≈ 1 token (English text)
Provides fast estimates without external tokenization libraries.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .models import ConversationTurn


@dataclass
class TokenUsage:
    """Token usage breakdown for a conversation."""
    system_prompt: int
    conversation_history: int
    workflow_context: int
    total: int
    percentage_of_limit: float

    def is_warning_threshold(self, threshold: float = 0.80) -> bool:
        """Check if usage exceeds warning threshold."""
        return self.percentage_of_limit >= (threshold * 100)

    def is_critical_threshold(self, threshold: float = 0.95) -> bool:
        """Check if usage exceeds critical threshold."""
        return self.percentage_of_limit >= (threshold * 100)


class TokenCounter:
    """
    Token counter with approximation for PoC.

    Design principles:
    - Fast approximation: 4 chars ≈ 1 token
    - Good enough for monitoring and warnings
    - No external dependencies (tiktoken, etc.)
    - Easy migration to exact counting later
    """

    # Approximation ratio for English text
    CHARS_PER_TOKEN = 4

    def __init__(self, context_window_limit: int = 32000):
        """
        Initialize token counter.

        Args:
            context_window_limit: Maximum tokens for model context window
        """
        self.context_window_limit = context_window_limit

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count from text.

        Args:
            text: Input text to count

        Returns:
            Approximate token count
        """
        if not text:
            return 0

        # Simple approximation: 4 characters ≈ 1 token
        char_count = len(text)
        return max(1, char_count // self.CHARS_PER_TOKEN)

    def count_conversation_tokens(
        self,
        turns: List[ConversationTurn]
    ) -> int:
        """
        Count tokens in conversation history.

        Args:
            turns: List of conversation turns

        Returns:
            Total token count for conversation
        """
        total_tokens = 0

        for turn in turns:
            # User message
            total_tokens += self.count_tokens(turn.user_message)
            # Agent response
            total_tokens += self.count_tokens(turn.agent_response)
            # Small overhead for formatting (User:/Agent: labels)
            total_tokens += 4

        return total_tokens

    def count_workflow_tokens(
        self,
        workflow_spec: Optional[Dict[str, Any]]
    ) -> int:
        """
        Count tokens in workflow specification context.

        Args:
            workflow_spec: Workflow specification dictionary

        Returns:
            Token count for workflow context
        """
        if not workflow_spec:
            return 0

        # Convert to string and count
        import json
        workflow_json = json.dumps(workflow_spec, indent=2)
        return self.count_tokens(workflow_json)

    def calculate_usage(
        self,
        system_prompt: str,
        conversation_history: str,
        workflow_spec: Optional[Dict[str, Any]] = None
    ) -> TokenUsage:
        """
        Calculate comprehensive token usage breakdown.

        Args:
            system_prompt: Current system prompt text
            conversation_history: Formatted conversation history
            workflow_spec: Optional workflow specification

        Returns:
            TokenUsage breakdown with percentages
        """
        # Count each component
        system_tokens = self.count_tokens(system_prompt)
        history_tokens = self.count_tokens(conversation_history)
        workflow_tokens = self.count_workflow_tokens(workflow_spec)

        # Calculate total
        total_tokens = system_tokens + history_tokens + workflow_tokens

        # Calculate percentage of limit
        percentage = (total_tokens / self.context_window_limit) * 100 if self.context_window_limit > 0 else 0.0

        return TokenUsage(
            system_prompt=system_tokens,
            conversation_history=history_tokens,
            workflow_context=workflow_tokens,
            total=total_tokens,
            percentage_of_limit=round(percentage, 2)
        )

    def get_remaining_tokens(self, current_usage: int) -> int:
        """
        Get remaining tokens in context window.

        Args:
            current_usage: Current token usage

        Returns:
            Remaining tokens available
        """
        return max(0, self.context_window_limit - current_usage)

    def estimate_turns_remaining(
        self,
        current_usage: int,
        avg_turn_tokens: int = 200
    ) -> int:
        """
        Estimate how many more conversation turns can fit.

        Args:
            current_usage: Current token usage
            avg_turn_tokens: Average tokens per turn (user + agent)

        Returns:
            Estimated remaining conversation turns
        """
        remaining = self.get_remaining_tokens(current_usage)
        if avg_turn_tokens <= 0:
            return 0

        return remaining // avg_turn_tokens

    def should_summarize(
        self,
        current_usage: int,
        threshold: float = 0.70
    ) -> bool:
        """
        Check if summarization should be triggered based on token usage.

        Args:
            current_usage: Current token count
            threshold: Percentage threshold (0.0-1.0)

        Returns:
            True if usage exceeds threshold
        """
        threshold_tokens = int(self.context_window_limit * threshold)
        return current_usage >= threshold_tokens

    def get_stats(self) -> Dict[str, Any]:
        """
        Get token counter configuration and stats.

        Returns:
            Dictionary with token counter settings
        """
        return {
            "context_window_limit": self.context_window_limit,
            "chars_per_token": self.CHARS_PER_TOKEN,
            "approximation_method": "4 chars per token (English text)",
            "warning_threshold": "80%",
            "critical_threshold": "95%"
        }


def create_token_counter(model_name: str = "gemini-2.5-flash-lite") -> TokenCounter:
    """
    Create token counter with appropriate context window for model.

    Args:
        model_name: AI model name

    Returns:
        TokenCounter configured for model's context window
    """
    # Context window limits by model
    MODEL_LIMITS = {
        "gemini-2.5-flash-lite": 32000,
        "gemini-1.5-pro": 128000,
        "gemini-1.5-flash": 32000,
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 16385,
    }

    # Default to 32K if model not found
    limit = MODEL_LIMITS.get(model_name, 32000)

    return TokenCounter(context_window_limit=limit)