"""
Workflow memory for tracking workflows discussed in conversations.

Implements "structured note-taking" pattern from Anthropic's context engineering:
- Lightweight references instead of full workflow specs
- Alias generation for flexible search
- Last N workflows for recent context
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class WorkflowReference:
    """Lightweight workflow reference for memory."""
    spec_id: str
    name: str
    action: str  # created, modified, discussed, viewed
    timestamp: datetime
    aliases: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)


class WorkflowMemory:
    """
    Tracks workflows discussed in a conversation with lightweight references.

    Design principles:
    - Keep references small (< 50 tokens each)
    - Store outside main context window
    - Enable semantic search via aliases
    - Track recency for context prioritization
    """

    def __init__(self, max_references: int = 50):
        """
        Initialize workflow memory.

        Args:
            max_references: Maximum workflow references to retain
        """
        self.max_references = max_references
        self._references: Dict[str, WorkflowReference] = {}
        self._access_order: List[str] = []  # LRU tracking

    def add_workflow(
        self,
        spec_id: str,
        name: str,
        action: str = "discussed",
        aliases: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None
    ):
        """
        Add or update a workflow reference.

        Args:
            spec_id: Workflow specification ID
            name: Business-friendly workflow name
            action: What happened (created, modified, discussed, viewed)
            aliases: Alternative names for search
            tags: Categorization tags
        """
        # Generate aliases if not provided
        if aliases is None:
            aliases = self._generate_aliases(name)

        if tags is None:
            tags = set()

        # Create or update reference
        reference = WorkflowReference(
            spec_id=spec_id,
            name=name,
            action=action,
            timestamp=datetime.now(),
            aliases=aliases,
            tags=tags
        )

        self._references[spec_id] = reference

        # Update LRU tracking
        if spec_id in self._access_order:
            self._access_order.remove(spec_id)
        self._access_order.append(spec_id)

        # Trim if exceeds max
        if len(self._references) > self.max_references:
            oldest_id = self._access_order.pop(0)
            if oldest_id in self._references:
                del self._references[oldest_id]

    def get_workflow(self, spec_id: str) -> Optional[WorkflowReference]:
        """
        Get a workflow reference by ID.

        Updates LRU on access.

        Args:
            spec_id: Workflow specification ID

        Returns:
            WorkflowReference if found, None otherwise
        """
        if spec_id not in self._references:
            return None

        # Update LRU
        if spec_id in self._access_order:
            self._access_order.remove(spec_id)
        self._access_order.append(spec_id)

        return self._references[spec_id]

    def search_workflows(self, query: str) -> List[WorkflowReference]:
        """
        Search workflows by name or aliases.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching workflow references, sorted by recency
        """
        query_lower = query.lower()
        matches = []

        for spec_id, ref in self._references.items():
            # Check name
            if query_lower in ref.name.lower():
                matches.append(ref)
                continue

            # Check aliases
            for alias in ref.aliases:
                if query_lower in alias.lower():
                    matches.append(ref)
                    break

        # Sort by recency (most recent first)
        matches.sort(key=lambda r: r.timestamp, reverse=True)
        return matches

    def get_recent_workflows(self, limit: int = 5) -> List[WorkflowReference]:
        """
        Get most recently accessed workflows.

        Args:
            limit: Maximum number of workflows to return

        Returns:
            List of recent workflow references
        """
        recent_ids = self._access_order[-limit:]
        recent_ids.reverse()  # Most recent first

        return [
            self._references[spec_id]
            for spec_id in recent_ids
            if spec_id in self._references
        ]

    def get_workflows_by_action(self, action: str) -> List[WorkflowReference]:
        """
        Get workflows filtered by action type.

        Args:
            action: Action type (created, modified, discussed, viewed)

        Returns:
            List of workflow references with matching action
        """
        matches = [
            ref for ref in self._references.values()
            if ref.action == action
        ]

        # Sort by recency
        matches.sort(key=lambda r: r.timestamp, reverse=True)
        return matches

    def get_workflows_by_tag(self, tag: str) -> List[WorkflowReference]:
        """
        Get workflows filtered by tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of workflow references with matching tag
        """
        matches = [
            ref for ref in self._references.values()
            if tag in ref.tags
        ]

        # Sort by recency
        matches.sort(key=lambda r: r.timestamp, reverse=True)
        return matches

    def format_for_context(self, limit: int = 5) -> str:
        """
        Format recent workflows for context window (compact representation).

        Args:
            limit: Maximum workflows to include

        Returns:
            Compact string representation for context
        """
        recent = self.get_recent_workflows(limit)

        if not recent:
            return ""

        lines = ["Recent workflows:"]
        for ref in recent:
            # Compact format: action + name + ID
            lines.append(f"- {ref.action}: {ref.name} ({ref.spec_id})")

        return "\n".join(lines)

    def get_stats(self) -> Dict:
        """
        Get memory statistics.

        Returns:
            Dictionary with memory metrics
        """
        actions_count = {}
        for ref in self._references.values():
            actions_count[ref.action] = actions_count.get(ref.action, 0) + 1

        all_tags = set()
        for ref in self._references.values():
            all_tags.update(ref.tags)

        return {
            "total_workflows": len(self._references),
            "max_references": self.max_references,
            "actions_count": actions_count,
            "total_tags": len(all_tags),
            "tags": sorted(list(all_tags))
        }

    def clear(self):
        """Clear all workflow references."""
        self._references.clear()
        self._access_order.clear()

    def _generate_aliases(self, name: str) -> List[str]:
        """
        Generate search aliases for a workflow name.

        Examples:
            "Document Approval" -> ["doc approval", "document", "approval"]
            "Task Management" -> ["task mgmt", "task", "management"]

        Args:
            name: Workflow name

        Returns:
            List of generated aliases
        """
        aliases = []
        name_lower = name.lower()

        # Add full name lowercase
        aliases.append(name_lower)

        # Split into words
        words = name_lower.split()

        # Add individual words (if multiple)
        if len(words) > 1:
            aliases.extend(words)

        # Common abbreviations
        abbreviations = {
            "approval": "appr",
            "document": "doc",
            "management": "mgmt",
            "request": "req",
            "process": "proc",
            "workflow": "wf",
            "system": "sys",
            "application": "app"
        }

        # Add abbreviated versions
        for word, abbr in abbreviations.items():
            if word in name_lower:
                aliases.append(name_lower.replace(word, abbr))

        # Remove duplicates and empty strings
        aliases = list(set(filter(None, aliases)))

        return aliases

    def export_references(self) -> List[Dict]:
        """
        Export all references as dictionaries for serialization.

        Returns:
            List of workflow reference dictionaries
        """
        return [
            {
                "spec_id": ref.spec_id,
                "name": ref.name,
                "action": ref.action,
                "timestamp": ref.timestamp.isoformat(),
                "aliases": ref.aliases,
                "tags": list(ref.tags)
            }
            for ref in self._references.values()
        ]

    def import_references(self, references: List[Dict]):
        """
        Import references from dictionaries.

        Args:
            references: List of workflow reference dictionaries
        """
        for ref_dict in references:
            self.add_workflow(
                spec_id=ref_dict["spec_id"],
                name=ref_dict["name"],
                action=ref_dict.get("action", "discussed"),
                aliases=ref_dict.get("aliases"),
                tags=set(ref_dict.get("tags", []))
            )