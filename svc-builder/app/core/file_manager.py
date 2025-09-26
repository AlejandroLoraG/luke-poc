import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from .settings import settings


class WorkflowFileManager:
    """Simple file-based workflow JSON manager for PoC."""

    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, spec_id: str) -> Path:
        """Get the file path for a workflow spec."""
        return self.storage_path / f"{spec_id}.json"

    def save_workflow(self, spec_id: str, workflow_data: Dict[str, Any]) -> bool:
        """
        Save workflow JSON to file.

        Args:
            spec_id: Workflow specification ID
            workflow_data: Workflow JSON data

        Returns:
            bool: True if saved successfully
        """
        try:
            file_path = self._get_file_path(spec_id)

            # Write to temporary file first, then rename (atomic operation)
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.rename(file_path)
            return True

        except Exception as e:
            print(f"Error saving workflow {spec_id}: {e}")
            return False

    def load_workflow(self, spec_id: str) -> Optional[Dict[str, Any]]:
        """
        Load workflow JSON from file.

        Args:
            spec_id: Workflow specification ID

        Returns:
            Workflow data or None if not found
        """
        try:
            file_path = self._get_file_path(spec_id)

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            print(f"Error loading workflow {spec_id}: {e}")
            return None

    def delete_workflow(self, spec_id: str) -> bool:
        """
        Delete workflow file.

        Args:
            spec_id: Workflow specification ID

        Returns:
            bool: True if deleted successfully
        """
        try:
            file_path = self._get_file_path(spec_id)

            if file_path.exists():
                file_path.unlink()
                return True
            else:
                return False

        except Exception as e:
            print(f"Error deleting workflow {spec_id}: {e}")
            return False

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all workflow files.

        Returns:
            List of workflow summaries
        """
        workflows = []

        try:
            for file_path in self.storage_path.glob("*.json"):
                if file_path.is_file():
                    spec_id = file_path.stem

                    # Try to load basic info
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        workflow_info = {
                            "spec_id": spec_id,
                            "name": data.get("name", "Unknown"),
                            "slug": data.get("slug", ""),
                            "tenant_id": data.get("tenantId", ""),
                            "version": data.get("specVersion", 1),
                            "states_count": len(data.get("states", [])),
                            "actions_count": len(data.get("actions", [])),
                            "file_size": file_path.stat().st_size,
                            "last_modified": file_path.stat().st_mtime
                        }
                        workflows.append(workflow_info)

                    except Exception as e:
                        # If file is corrupted, still list it
                        workflows.append({
                            "spec_id": spec_id,
                            "name": "Error loading",
                            "error": str(e),
                            "file_size": file_path.stat().st_size,
                            "last_modified": file_path.stat().st_mtime
                        })

        except Exception as e:
            print(f"Error listing workflows: {e}")

        return workflows

    def workflow_exists(self, spec_id: str) -> bool:
        """
        Check if workflow file exists.

        Args:
            spec_id: Workflow specification ID

        Returns:
            bool: True if file exists
        """
        file_path = self._get_file_path(spec_id)
        return file_path.exists()

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        try:
            files = list(self.storage_path.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files if f.is_file())

            return {
                "total_workflows": len(files),
                "storage_path": str(self.storage_path.absolute()),
                "total_size_bytes": total_size,
                "workflow_ids": [f.stem for f in files if f.is_file()]
            }
        except Exception as e:
            return {
                "total_workflows": 0,
                "error": str(e),
                "storage_path": str(self.storage_path.absolute())
            }


# Global file manager instance
file_manager = WorkflowFileManager()