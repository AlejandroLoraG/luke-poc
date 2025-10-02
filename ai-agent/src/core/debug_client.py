"""
Debug client for direct svc-builder API access.

This module provides a diagnostic client that bypasses the MCP layer
and makes direct HTTP calls to the svc-builder service. This is useful
for diagnosing whether issues occur in the MCP tool calling layer or
in the svc-builder service itself.

Enable via DEBUG_MODE=true environment variable.
"""

import logging
import httpx
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DebugWorkflowClient:
    """
    Direct HTTP client for svc-builder API diagnostics.

    This client bypasses MCP and makes direct API calls to svc-builder,
    allowing us to isolate whether issues are in:
    - MCP tool calling layer
    - svc-builder service
    - Network communication
    """

    def __init__(self, svc_builder_url: str):
        """
        Initialize debug client.

        Args:
            svc_builder_url: Base URL for svc-builder service (e.g., http://svc-builder:8000)
        """
        self.base_url = svc_builder_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"DebugWorkflowClient initialized with base URL: {self.base_url}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def create_workflow_direct(self, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a workflow via direct API call.

        Args:
            workflow_spec: Complete workflow specification dictionary

        Returns:
            API response with created workflow details

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.api_base}/workflows"
        logger.debug(f"DEBUG MODE: Direct POST to {url}")
        logger.debug(f"DEBUG MODE: Payload spec_id={workflow_spec.get('specId', 'unknown')}")

        try:
            response = await self.client.post(url, json=workflow_spec)
            response.raise_for_status()
            result = response.json()

            logger.info(f"DEBUG MODE: Workflow created successfully via direct API: {result.get('spec_id', 'unknown')}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"DEBUG MODE: Direct API call failed: {e}")
            logger.error(f"DEBUG MODE: Response status: {getattr(e.response, 'status_code', 'N/A')}")
            logger.error(f"DEBUG MODE: Response body: {getattr(e.response, 'text', 'N/A')}")
            raise

    async def get_workflow_direct(self, spec_id: str) -> Dict[str, Any]:
        """
        Get a workflow via direct API call.

        Args:
            spec_id: Workflow specification ID

        Returns:
            Workflow specification dictionary

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.api_base}/workflows/{spec_id}"
        logger.debug(f"DEBUG MODE: Direct GET to {url}")

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            result = response.json()

            logger.info(f"DEBUG MODE: Workflow retrieved successfully via direct API: {spec_id}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"DEBUG MODE: Direct API call failed: {e}")
            logger.error(f"DEBUG MODE: Response status: {getattr(e.response, 'status_code', 'N/A')}")
            raise

    async def list_workflows_direct(self) -> Dict[str, Any]:
        """
        List all workflows via direct API call.

        Returns:
            Dictionary with workflows list and count

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.api_base}/workflows"
        logger.debug(f"DEBUG MODE: Direct GET to {url}")

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            result = response.json()

            count = len(result.get('workflows', []))
            logger.info(f"DEBUG MODE: Listed {count} workflows via direct API")
            return result

        except httpx.HTTPError as e:
            logger.error(f"DEBUG MODE: Direct API call failed: {e}")
            raise

    async def update_workflow_direct(self, spec_id: str, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a workflow via direct API call.

        Args:
            spec_id: Workflow specification ID
            workflow_spec: Updated workflow specification dictionary

        Returns:
            API response with updated workflow details

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.api_base}/workflows/{spec_id}"
        logger.debug(f"DEBUG MODE: Direct PUT to {url}")

        try:
            response = await self.client.put(url, json=workflow_spec)
            response.raise_for_status()
            result = response.json()

            logger.info(f"DEBUG MODE: Workflow updated successfully via direct API: {spec_id}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"DEBUG MODE: Direct API call failed: {e}")
            logger.error(f"DEBUG MODE: Response status: {getattr(e.response, 'status_code', 'N/A')}")
            logger.error(f"DEBUG MODE: Response body: {getattr(e.response, 'text', 'N/A')}")
            raise

    async def delete_workflow_direct(self, spec_id: str) -> Dict[str, Any]:
        """
        Delete a workflow via direct API call.

        Args:
            spec_id: Workflow specification ID

        Returns:
            API response confirming deletion

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.api_base}/workflows/{spec_id}"
        logger.debug(f"DEBUG MODE: Direct DELETE to {url}")

        try:
            response = await self.client.delete(url)
            response.raise_for_status()
            result = response.json()

            logger.info(f"DEBUG MODE: Workflow deleted successfully via direct API: {spec_id}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"DEBUG MODE: Direct API call failed: {e}")
            raise

    async def health_check_direct(self) -> Dict[str, Any]:
        """
        Check svc-builder health via direct API call.

        Returns:
            Health check response

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.api_base}/health"
        logger.debug(f"DEBUG MODE: Direct GET to {url}")

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            result = response.json()

            logger.info(f"DEBUG MODE: svc-builder health check successful: {result.get('status', 'unknown')}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"DEBUG MODE: Health check failed: {e}")
            raise
