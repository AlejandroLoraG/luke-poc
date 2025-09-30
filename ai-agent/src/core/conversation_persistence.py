"""
Conversation persistence layer for ConversationManager.

Provides file-based storage with atomic writes and automatic save/load.
"""

import json
import os
import tempfile
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

from .models import ConversationTurn


@dataclass
class PersistedConversation:
    """Persisted conversation with metadata."""
    conversation_id: str
    turns: List[Dict]
    created_at: str
    updated_at: str
    turn_count: int


class ConversationPersistence:
    """
    File-based persistence for conversations with atomic writes.

    Features:
    - Atomic writes using temp file + rename pattern
    - JSON format for human readability
    - Automatic save on conversation updates
    - Graceful degradation on errors
    - Directory-based storage (one file per conversation)
    """

    def __init__(self, storage_dir: str = "storage/conversations"):
        """
        Initialize conversation persistence.

        Args:
            storage_dir: Directory to store conversation files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_conversation_path(self, conversation_id: str) -> Path:
        """Get file path for a conversation."""
        # Sanitize conversation_id to be filesystem-safe
        safe_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in conversation_id)
        return self.storage_dir / f"{safe_id}.json"

    def save_conversation(
        self,
        conversation_id: str,
        turns: List[ConversationTurn],
        created_at: Optional[datetime] = None
    ) -> bool:
        """
        Save conversation to disk using atomic write.

        Args:
            conversation_id: Unique conversation identifier
            turns: List of conversation turns to persist
            created_at: Timestamp when conversation was created

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            # Convert turns to dicts for JSON serialization
            turns_data = [
                {
                    "user_message": turn.user_message,
                    "agent_response": turn.agent_response,
                    "timestamp": turn.timestamp.isoformat(),
                    "mcp_tools_used": turn.mcp_tools_used
                }
                for turn in turns
            ]

            # Prepare conversation data
            now = datetime.now().isoformat()
            conversation_data = {
                "conversation_id": conversation_id,
                "turns": turns_data,
                "created_at": created_at.isoformat() if created_at else now,
                "updated_at": now,
                "turn_count": len(turns)
            }

            # Atomic write: write to temp file, then rename
            file_path = self._get_conversation_path(conversation_id)
            # Use sanitized ID for temp file prefix
            safe_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in conversation_id)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.storage_dir,
                prefix=f".tmp_{safe_id}_",
                suffix=".json"
            )

            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(conversation_data, f, indent=2)

                # Atomic rename
                os.replace(temp_path, file_path)
                return True

            except Exception as e:
                # Cleanup temp file on error
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise e

        except Exception as e:
            print(f"Error saving conversation {conversation_id}: {e}")
            return False

    def load_conversation(self, conversation_id: str) -> Optional[List[ConversationTurn]]:
        """
        Load conversation from disk.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            List of conversation turns if found, None otherwise
        """
        try:
            file_path = self._get_conversation_path(conversation_id)

            if not file_path.exists():
                return None

            with open(file_path, 'r') as f:
                data = json.load(f)

            # Reconstruct ConversationTurn objects
            turns = []
            for turn_data in data.get("turns", []):
                turn = ConversationTurn(
                    user_message=turn_data["user_message"],
                    agent_response=turn_data["agent_response"],
                    timestamp=datetime.fromisoformat(turn_data["timestamp"]),
                    mcp_tools_used=turn_data.get("mcp_tools_used", [])
                )
                turns.append(turn)

            return turns

        except Exception as e:
            print(f"Error loading conversation {conversation_id}: {e}")
            return None

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation from disk.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            file_path = self._get_conversation_path(conversation_id)

            if file_path.exists():
                file_path.unlink()
                return True

            return False

        except Exception as e:
            print(f"Error deleting conversation {conversation_id}: {e}")
            return False

    def list_conversations(self) -> List[Dict]:
        """
        List all persisted conversations with metadata.

        Returns:
            List of conversation metadata dictionaries
        """
        try:
            conversations = []

            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)

                    conversations.append({
                        "conversation_id": data.get("conversation_id"),
                        "turn_count": data.get("turn_count", 0),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at")
                    })

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

            return conversations

        except Exception as e:
            print(f"Error listing conversations: {e}")
            return []

    def get_stats(self) -> Dict:
        """
        Get persistence statistics.

        Returns:
            Dictionary with storage statistics
        """
        try:
            conversations = self.list_conversations()
            total_turns = sum(c.get("turn_count", 0) for c in conversations)
            total_size = sum(
                f.stat().st_size
                for f in self.storage_dir.glob("*.json")
            )

            return {
                "total_conversations": len(conversations),
                "total_turns": total_turns,
                "storage_size_bytes": total_size,
                "storage_dir": str(self.storage_dir)
            }

        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                "total_conversations": 0,
                "total_turns": 0,
                "storage_size_bytes": 0,
                "storage_dir": str(self.storage_dir),
                "error": str(e)
            }

    def clear_all(self) -> int:
        """
        Clear all persisted conversations.

        Returns:
            Number of conversations deleted
        """
        try:
            count = 0
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    file_path.unlink()
                    count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

            return count

        except Exception as e:
            print(f"Error clearing conversations: {e}")
            return 0