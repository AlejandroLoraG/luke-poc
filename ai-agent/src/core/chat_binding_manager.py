"""
Chat Binding Management Layer

Manages chat-to-workflow bindings with file-based persistence.
Enforces the one-workflow-per-chat rule following Pydantic AI best practices.
"""

import json
import os
import tempfile
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

from .models import ChatBinding

logger = logging.getLogger(__name__)


class ChatBindingManager:
    """
    File-based chat binding management with atomic writes.

    Features:
    - Track chat-to-workflow bindings
    - Enforce one-workflow-per-chat rule
    - File persistence for durability (JSON format)
    - Atomic writes using temp file + rename pattern
    - Automatic loading on initialization
    - Type-safe ChatBinding models
    """

    def __init__(self, storage_dir: str = "storage/chat_bindings"):
        """
        Initialize chat binding manager with file-based storage.

        Args:
            storage_dir: Directory to store binding files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._bindings: Dict[str, ChatBinding] = {}
        self._load_bindings()
        logger.info(f"ChatBindingManager initialized with storage: {self.storage_dir}")

    def create_binding(
        self,
        conversation_id: str,
        session_id: str
    ) -> ChatBinding:
        """
        Create a new chat binding (not yet bound to any workflow).

        Args:
            conversation_id: Unique conversation identifier
            session_id: Parent session identifier

        Returns:
            Newly created ChatBinding object
        """
        # Check if binding already exists
        if conversation_id in self._bindings:
            logger.warning(f"Binding already exists for conversation: {conversation_id}")
            return self._bindings[conversation_id]

        now = datetime.now()
        binding = ChatBinding(
            conversation_id=conversation_id,
            session_id=session_id,
            created_at=now,
            bound_workflow_id=None,
            binding_locked_at=None,
            last_activity=now
        )

        self._bindings[conversation_id] = binding
        self._persist_binding(binding)

        logger.info(f"✨ Created chat binding: {conversation_id} in session: {session_id}")
        return binding

    def bind_workflow(
        self,
        conversation_id: str,
        workflow_id: str
    ) -> ChatBinding:
        """
        Bind a chat to a specific workflow.

        Args:
            conversation_id: Unique conversation identifier
            workflow_id: Workflow spec ID to bind

        Returns:
            Updated ChatBinding object

        Raises:
            ValueError: If chat is already bound to a different workflow
            KeyError: If binding doesn't exist
        """
        binding = self._bindings.get(conversation_id)
        if not binding:
            raise KeyError(f"No binding found for conversation: {conversation_id}")

        # Attempt to bind
        try:
            binding.bind(workflow_id)
            self._persist_binding(binding)
            logger.info(f"🔒 Bound chat {conversation_id} to workflow {workflow_id}")
            return binding
        except ValueError as e:
            logger.error(f"Failed to bind workflow: {e}")
            raise

    def get_binding(self, conversation_id: str) -> Optional[ChatBinding]:
        """
        Get binding information for a conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            ChatBinding object if found, None otherwise
        """
        return self._bindings.get(conversation_id)

    def is_bound(self, conversation_id: str) -> bool:
        """
        Check if a conversation is bound to a workflow.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if bound, False otherwise
        """
        binding = self._bindings.get(conversation_id)
        return binding.is_bound() if binding else False

    def get_bound_workflow(self, conversation_id: str) -> Optional[str]:
        """
        Get the workflow ID bound to a conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Workflow spec ID if bound, None otherwise
        """
        binding = self._bindings.get(conversation_id)
        return binding.bound_workflow_id if binding else None

    def update_activity(self, conversation_id: str) -> bool:
        """
        Update last activity timestamp for a binding.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if binding was updated, False if not found
        """
        binding = self._bindings.get(conversation_id)
        if not binding:
            return False

        binding.update_activity()
        self._persist_binding(binding)
        return True

    def get_session_bindings(self, session_id: str) -> List[ChatBinding]:
        """
        Get all chat bindings for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of ChatBinding objects
        """
        return [
            binding for binding in self._bindings.values()
            if binding.session_id == session_id
        ]

    def delete_binding(self, conversation_id: str) -> bool:
        """
        Delete a chat binding and its persistent storage.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if binding was deleted, False if not found
        """
        if conversation_id not in self._bindings:
            return False

        # Remove from memory
        del self._bindings[conversation_id]

        # Remove from disk
        binding_path = self._get_binding_path(conversation_id)
        try:
            if binding_path.exists():
                binding_path.unlink()
                logger.info(f"🗑️  Deleted binding: {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting binding {conversation_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, any]:
        """
        Get binding manager statistics.

        Returns:
            Dictionary with binding metrics
        """
        total_bindings = len(self._bindings)
        bound_count = sum(1 for b in self._bindings.values() if b.is_bound())

        return {
            "total_bindings": total_bindings,
            "bound_count": bound_count,
            "unbound_count": total_bindings - bound_count,
            "storage_dir": str(self.storage_dir),
            "storage_exists": self.storage_dir.exists()
        }

    # Private methods

    def _get_binding_path(self, conversation_id: str) -> Path:
        """Get file path for a chat binding."""
        safe_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in conversation_id)
        return self.storage_dir / f"{safe_id}.json"

    def _persist_binding(self, binding: ChatBinding) -> bool:
        """
        Persist chat binding to disk using atomic write.

        Args:
            binding: ChatBinding object to persist

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            binding_data = {
                "conversation_id": binding.conversation_id,
                "session_id": binding.session_id,
                "created_at": binding.created_at.isoformat(),
                "bound_workflow_id": binding.bound_workflow_id,
                "binding_locked_at": binding.binding_locked_at.isoformat() if binding.binding_locked_at else None,
                "last_activity": binding.last_activity.isoformat()
            }

            binding_path = self._get_binding_path(binding.conversation_id)

            # Atomic write: temp file + rename
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.storage_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                json.dump(binding_data, tmp_file, indent=2)
                tmp_path = tmp_file.name

            # Atomic rename
            os.replace(tmp_path, binding_path)
            return True

        except Exception as e:
            logger.error(f"Failed to persist binding {binding.conversation_id}: {e}")
            return False

    def _load_bindings(self):
        """Load all chat bindings from disk on initialization."""
        if not self.storage_dir.exists():
            logger.info("No binding storage directory found, starting fresh")
            return

        loaded_count = 0
        for binding_file in self.storage_dir.glob("*.json"):
            try:
                with open(binding_file, 'r') as f:
                    data = json.load(f)

                binding = ChatBinding(
                    conversation_id=data["conversation_id"],
                    session_id=data["session_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    bound_workflow_id=data.get("bound_workflow_id"),
                    binding_locked_at=datetime.fromisoformat(data["binding_locked_at"]) if data.get("binding_locked_at") else None,
                    last_activity=datetime.fromisoformat(data["last_activity"])
                )

                self._bindings[binding.conversation_id] = binding
                loaded_count += 1

            except Exception as e:
                logger.error(f"Failed to load binding from {binding_file}: {e}")

        if loaded_count > 0:
            logger.info(f"📂 Loaded {loaded_count} chat binding(s) from storage")
