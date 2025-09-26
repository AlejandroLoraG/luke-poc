from typing import Dict, List, Optional, Any
from datetime import datetime
from ..data.sample_workflows import SAMPLE_WORKFLOWS


class WorkflowStorage:
    """In-memory workflow storage for development and testing."""

    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._initialize_samples()

    def _initialize_samples(self):
        """Load sample workflows into storage."""
        for workflow_id, workflow_data in SAMPLE_WORKFLOWS.items():
            self._workflows[workflow_id] = workflow_data.copy()
            self._metadata[workflow_id] = {
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_sample": True,
                "version": workflow_data.get("specVersion", 1)
            }

    def store_workflow(
        self,
        workflow_id: str,
        workflow_data: Dict[str, Any],
        overwrite: bool = False
    ) -> bool:
        """
        Store a workflow in memory.

        Args:
            workflow_id: Unique identifier for the workflow
            workflow_data: The workflow specification
            overwrite: Whether to overwrite existing workflows

        Returns:
            bool: True if stored successfully, False if workflow exists and overwrite=False
        """
        if workflow_id in self._workflows and not overwrite:
            return False

        self._workflows[workflow_id] = workflow_data.copy()

        now = datetime.now()
        if workflow_id in self._metadata:
            self._metadata[workflow_id]["updated_at"] = now
        else:
            self._metadata[workflow_id] = {
                "created_at": now,
                "updated_at": now,
                "is_sample": False,
                "version": workflow_data.get("specVersion", 1)
            }

        return True

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a workflow by ID.

        Args:
            workflow_id: The workflow identifier

        Returns:
            The workflow data or None if not found
        """
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all stored workflows with metadata.

        Returns:
            List of workflow summaries
        """
        workflows = []
        for workflow_id, workflow_data in self._workflows.items():
            metadata = self._metadata.get(workflow_id, {})
            workflows.append({
                "workflow_id": workflow_id,
                "spec_id": workflow_data.get("specId", workflow_id),
                "name": workflow_data.get("name", "Unknown"),
                "slug": workflow_data.get("slug", ""),
                "tenant_id": workflow_data.get("tenantId", ""),
                "version": workflow_data.get("specVersion", 1),
                "states_count": len(workflow_data.get("states", [])),
                "actions_count": len(workflow_data.get("actions", [])),
                "is_sample": metadata.get("is_sample", False),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at")
            })

        return workflows

    def update_workflow(
        self,
        workflow_id: str,
        workflow_data: Dict[str, Any]
    ) -> bool:
        """
        Update an existing workflow.

        Args:
            workflow_id: The workflow identifier
            workflow_data: The updated workflow specification

        Returns:
            bool: True if updated successfully, False if workflow doesn't exist
        """
        if workflow_id not in self._workflows:
            return False

        self._workflows[workflow_id] = workflow_data.copy()
        self._metadata[workflow_id]["updated_at"] = datetime.now()
        self._metadata[workflow_id]["version"] = workflow_data.get("specVersion", 1)

        return True

    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow from storage.

        Args:
            workflow_id: The workflow identifier

        Returns:
            bool: True if deleted successfully, False if workflow doesn't exist
        """
        if workflow_id not in self._workflows:
            return False

        del self._workflows[workflow_id]
        del self._metadata[workflow_id]

        return True

    def workflow_exists(self, workflow_id: str) -> bool:
        """
        Check if a workflow exists.

        Args:
            workflow_id: The workflow identifier

        Returns:
            bool: True if workflow exists
        """
        return workflow_id in self._workflows

    def get_workflow_metadata(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific workflow.

        Args:
            workflow_id: The workflow identifier

        Returns:
            Metadata dict or None if workflow doesn't exist
        """
        return self._metadata.get(workflow_id)

    def clear_all_workflows(self, keep_samples: bool = True):
        """
        Clear all workflows from storage.

        Args:
            keep_samples: Whether to keep sample workflows
        """
        if keep_samples:
            # Keep only sample workflows
            workflow_ids_to_remove = [
                wf_id for wf_id, metadata in self._metadata.items()
                if not metadata.get("is_sample", False)
            ]
            for workflow_id in workflow_ids_to_remove:
                self.delete_workflow(workflow_id)
        else:
            self._workflows.clear()
            self._metadata.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        total_workflows = len(self._workflows)
        sample_workflows = sum(
            1 for metadata in self._metadata.values()
            if metadata.get("is_sample", False)
        )
        custom_workflows = total_workflows - sample_workflows

        return {
            "total_workflows": total_workflows,
            "sample_workflows": sample_workflows,
            "custom_workflows": custom_workflows,
            "workflow_ids": list(self._workflows.keys())
        }


# Global workflow storage instance
workflow_storage = WorkflowStorage()