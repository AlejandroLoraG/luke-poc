"""
Core data models for conversation management.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class ConversationTurn:
    user_message: str
    agent_response: str
    timestamp: datetime
    mcp_tools_used: List[str]