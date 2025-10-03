"""
Core data models for conversation management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class Session:
    """
    User session grouping multiple chats.

    A session represents a user's workspace where they can have multiple
    concurrent conversations, each potentially bound to different workflows.
    """
    session_id: str
    created_at: datetime
    last_activity: datetime
    user_identifier: str  # Manual ID, IP, or browser fingerprint
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


@dataclass
class ChatBinding:
    """
    Tracks chat-to-workflow binding.

    Each conversation can be bound to exactly one workflow after creation.
    Once bound, the chat can interact with (view/update) only that workflow.
    """
    conversation_id: str
    session_id: str
    created_at: datetime
    bound_workflow_id: Optional[str] = None  # Set when workflow created/bound
    binding_locked_at: Optional[datetime] = None  # When workflow was bound
    last_activity: datetime = field(default_factory=datetime.now)

    def is_bound(self) -> bool:
        """Check if this chat is bound to a workflow."""
        return self.bound_workflow_id is not None

    def can_create_workflow(self) -> bool:
        """Can only create workflow if not already bound."""
        return not self.is_bound()

    def bind(self, workflow_id: str):
        """Bind this chat to a workflow."""
        if self.is_bound():
            raise ValueError(f"Chat {self.conversation_id} is already bound to {self.bound_workflow_id}")
        self.bound_workflow_id = workflow_id
        self.binding_locked_at = datetime.now()
        self.last_activity = datetime.now()

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


@dataclass
class ConversationTurn:
    """
    A single turn in a conversation.

    Now tracks the workflow context for each turn to support
    workflow-bound conversations.
    """
    user_message: str
    agent_response: str
    timestamp: datetime
    mcp_tools_used: List[str]
    workflow_id: Optional[str] = None  # Track workflow context per turn