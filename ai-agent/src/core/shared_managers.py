"""
Shared manager instances for the AI Agent.

This module provides singleton instances of SessionManager and ChatBindingManager
that are shared across all routers to ensure consistency.
"""

from .session_manager import SessionManager
from .chat_binding_manager import ChatBindingManager

# Singleton instances shared across all routers
session_manager = SessionManager()
chat_binding_manager = ChatBindingManager()
