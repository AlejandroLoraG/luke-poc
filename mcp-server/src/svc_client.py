import httpx
from typing import Dict, Any, List, Optional
import json
from config import settings


class SvcBuilderClient:
    """HTTP client for communicating with svc-builder service."""

    def __init__(self):
        self.base_url = settings.svc_builder_url.rstrip("/")
        self.timeout = settings.svc_builder_timeout

    async def get_workflow(self, spec_id: str) -> Dict[str, Any]:
        """
        Get a workflow specification from svc-builder.

        Args:
            spec_id: Workflow specification ID

        Returns:
            Workflow data from svc-builder

        Raises:
            Exception: If workflow not found or request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/v1/workflows/{spec_id}")

            if response.status_code == 404:
                raise Exception(f"Workflow '{spec_id}' not found")
            elif response.status_code != 200:
                raise Exception(f"Failed to get workflow: {response.status_code} - {response.text}")

            return response.json()

    async def list_workflows(self) -> Dict[str, Any]:
        """
        List all workflows from svc-builder.

        Returns:
            List of workflows with metadata
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/v1/workflows")

            if response.status_code != 200:
                raise Exception(f"Failed to list workflows: {response.status_code} - {response.text}")

            return response.json()

    async def create_workflow(self, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow in svc-builder.

        Args:
            workflow_spec: Complete workflow specification

        Returns:
            Creation result from svc-builder
        """
        payload = {"workflow_spec": workflow_spec}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/workflows",
                json=payload
            )

            if response.status_code == 409:
                raise Exception(f"Workflow with spec_id '{workflow_spec.get('specId')}' already exists")
            elif response.status_code != 201:
                raise Exception(f"Failed to create workflow: {response.status_code} - {response.text}")

            return response.json()

    async def update_workflow(self, spec_id: str, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing workflow in svc-builder.

        Args:
            spec_id: Workflow specification ID
            workflow_spec: Updated workflow specification

        Returns:
            Update result from svc-builder
        """
        payload = {"workflow_spec": workflow_spec}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.base_url}/api/v1/workflows/{spec_id}",
                json=payload
            )

            if response.status_code == 404:
                raise Exception(f"Workflow '{spec_id}' not found")
            elif response.status_code != 200:
                raise Exception(f"Failed to update workflow: {response.status_code} - {response.text}")

            return response.json()

    async def delete_workflow(self, spec_id: str) -> Dict[str, Any]:
        """
        Delete a workflow from svc-builder.

        Args:
            spec_id: Workflow specification ID

        Returns:
            Deletion result from svc-builder
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(f"{self.base_url}/api/v1/workflows/{spec_id}")

            if response.status_code == 404:
                raise Exception(f"Workflow '{spec_id}' not found")
            elif response.status_code != 200:
                raise Exception(f"Failed to delete workflow: {response.status_code} - {response.text}")

            return response.json()

    async def validate_workflow(self, spec_id: str) -> Dict[str, Any]:
        """
        Validate a workflow in svc-builder.

        Args:
            spec_id: Workflow specification ID

        Returns:
            Validation result from svc-builder
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/v1/workflows/{spec_id}/validate")

            if response.status_code == 404:
                raise Exception(f"Workflow '{spec_id}' not found")
            elif response.status_code != 200:
                raise Exception(f"Failed to validate workflow: {response.status_code} - {response.text}")

            return response.json()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check svc-builder service health.

        Returns:
            Health status from svc-builder
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/v1/health")

            if response.status_code != 200:
                raise Exception(f"svc-builder health check failed: {response.status_code}")

            return response.json()


# Global client instance
svc_client = SvcBuilderClient()