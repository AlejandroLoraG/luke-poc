import pytest
from unittest.mock import AsyncMock, patch
import asyncio

# Import the MCP server components
from src.svc_client import SvcBuilderClient
from src.config import settings


@pytest.mark.asyncio
async def test_svc_client_get_workflow():
    """Test the svc-builder client get_workflow method."""
    client = SvcBuilderClient()

    # Mock response
    mock_response_data = {
        "spec_id": "test_workflow",
        "workflow_spec": {
            "specId": "test_workflow",
            "name": "Test Workflow",
            "states": [],
            "actions": [],
            "permissions": [],
            "automations": []
        }
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await client.get_workflow("test_workflow")

        assert result == mock_response_data


@pytest.mark.asyncio
async def test_svc_client_list_workflows():
    """Test the svc-builder client list_workflows method."""
    client = SvcBuilderClient()

    mock_response_data = {
        "workflows": [
            {"spec_id": "wf1", "name": "Workflow 1"},
            {"spec_id": "wf2", "name": "Workflow 2"}
        ],
        "total_count": 2,
        "storage_stats": {"total_workflows": 2}
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await client.list_workflows()

        assert result == mock_response_data
        assert result["total_count"] == 2


@pytest.mark.asyncio
async def test_svc_client_create_workflow():
    """Test the svc-builder client create_workflow method."""
    client = SvcBuilderClient()

    workflow_spec = {
        "specId": "new_workflow",
        "name": "New Workflow",
        "tenantId": "test_tenant",
        "states": [{"slug": "start", "name": "Start", "type": "initial"}],
        "actions": [],
        "permissions": [],
        "automations": []
    }

    mock_response_data = {
        "message": "Workflow created successfully",
        "spec_id": "new_workflow"
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_response_data

        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        result = await client.create_workflow(workflow_spec)

        assert result == mock_response_data


@pytest.mark.asyncio
async def test_svc_client_error_handling():
    """Test error handling in svc-builder client."""
    client = SvcBuilderClient()

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            await client.get_workflow("nonexistent_workflow")

        assert "not found" in str(exc_info.value).lower()


def test_config_settings():
    """Test configuration settings."""
    assert settings.mcp_server_port == 8002
    assert settings.svc_builder_url == "http://localhost:8000"
    assert settings.server_name == "Workflow Management MCP Server"


@pytest.mark.asyncio
async def test_svc_client_health_check():
    """Test the health check functionality."""
    client = SvcBuilderClient()

    mock_health_data = {
        "status": "healthy",
        "service": "svc-builder",
        "storage": {"total_workflows": 3}
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_health_data

        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await client.health_check()

        assert result == mock_health_data
        assert result["status"] == "healthy"