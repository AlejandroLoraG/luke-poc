"""
Session Management Layer

Manages user sessions with file-based persistence following Pydantic AI best practices.
Sessions group multiple chats for organizational purposes without requiring authentication.
"""

import json
import os
import tempfile
import uuid
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

from .models import Session

logger = logging.getLogger(__name__)


class SessionManager:
    """
    File-based session management with atomic writes.

    Features:
    - Create and manage user sessions
    - File persistence for durability (JSON format)
    - Atomic writes using temp file + rename pattern
    - Automatic loading on initialization
    - Type-safe Session models
    """

    def __init__(self, storage_dir: str = "storage/sessions"):
        """
        Initialize session manager with file-based storage.

        Args:
            storage_dir: Directory to store session files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Session] = {}
        self._load_sessions()
        logger.info(f"SessionManager initialized with storage: {self.storage_dir}")

    def create_session(self, user_identifier: str = "anonymous") -> Session:
        """
        Create a new user session.

        Args:
            user_identifier: Optional identifier (IP, browser fingerprint, or manual ID)

        Returns:
            Newly created Session object
        """
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        now = datetime.now()

        session = Session(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            user_identifier=user_identifier,
            metadata={}
        )

        self._sessions[session_id] = session
        self._persist_session(session)

        logger.info(f"✨ Created session: {session_id} for user: {user_identifier}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            Session object if found, None otherwise
        """
        return self._sessions.get(session_id)

    def update_activity(self, session_id: str) -> bool:
        """
        Update last activity timestamp for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session was updated, False if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.update_activity()
        self._persist_session(session)
        return True

    def list_sessions(self, limit: int = 50) -> List[Session]:
        """
        List all sessions, most recent first.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of Session objects
        """
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.last_activity,
            reverse=True
        )
        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its persistent storage.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session was deleted, False if not found
        """
        if session_id not in self._sessions:
            return False

        # Remove from memory
        del self._sessions[session_id]

        # Remove from disk
        session_path = self._get_session_path(session_id)
        try:
            if session_path.exists():
                session_path.unlink()
                logger.info(f"🗑️  Deleted session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, any]:
        """
        Get session manager statistics.

        Returns:
            Dictionary with session metrics
        """
        return {
            "total_sessions": len(self._sessions),
            "storage_dir": str(self.storage_dir),
            "storage_exists": self.storage_dir.exists()
        }

    # Private methods

    def _get_session_path(self, session_id: str) -> Path:
        """Get file path for a session."""
        safe_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in session_id)
        return self.storage_dir / f"{safe_id}.json"

    def _persist_session(self, session: Session) -> bool:
        """
        Persist session to disk using atomic write.

        Args:
            session: Session object to persist

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            session_data = {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "user_identifier": session.user_identifier,
                "metadata": session.metadata
            }

            session_path = self._get_session_path(session.session_id)

            # Atomic write: temp file + rename
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.storage_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                json.dump(session_data, tmp_file, indent=2)
                tmp_path = tmp_file.name

            # Atomic rename
            os.replace(tmp_path, session_path)
            return True

        except Exception as e:
            logger.error(f"Failed to persist session {session.session_id}: {e}")
            return False

    def _load_sessions(self):
        """Load all sessions from disk on initialization."""
        if not self.storage_dir.exists():
            logger.info("No session storage directory found, starting fresh")
            return

        loaded_count = 0
        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)

                session = Session(
                    session_id=data["session_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    last_activity=datetime.fromisoformat(data["last_activity"]),
                    user_identifier=data["user_identifier"],
                    metadata=data.get("metadata", {})
                )

                self._sessions[session.session_id] = session
                loaded_count += 1

            except Exception as e:
                logger.error(f"Failed to load session from {session_file}: {e}")

        if loaded_count > 0:
            logger.info(f"📂 Loaded {loaded_count} session(s) from storage")
