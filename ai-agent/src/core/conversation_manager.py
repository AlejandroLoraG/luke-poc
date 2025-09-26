from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ConversationTurn:
    user_message: str
    agent_response: str
    timestamp: datetime
    mcp_tools_used: List[str]


class ConversationManager:
    def __init__(self, max_length: int = 15):
        self.max_length = max_length
        self.conversations: Dict[str, List[ConversationTurn]] = {}

    def add_turn(
        self,
        conversation_id: str,
        user_message: str,
        agent_response: str,
        mcp_tools_used: List[str] = None
    ) -> int:
        if mcp_tools_used is None:
            mcp_tools_used = []

        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

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

        return len(self.conversations[conversation_id])

    def get_conversation_history(self, conversation_id: str) -> List[ConversationTurn]:
        return self.conversations.get(conversation_id, [])

    def get_context_string(self, conversation_id: str) -> str:
        history = self.get_conversation_history(conversation_id)
        if not history:
            return ""

        context_parts = []
        for turn in history:
            context_parts.append(f"User: {turn.user_message}")
            context_parts.append(f"Agent: {turn.agent_response}")

        return "\n\n".join(context_parts)

    def get_conversation_count(self, conversation_id: str) -> int:
        return len(self.conversations.get(conversation_id, []))

    def clear_conversation(self, conversation_id: str):
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]