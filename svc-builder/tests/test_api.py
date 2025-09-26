import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.core.file_manager import file_manager


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "svc-builder"
    assert "version" in data


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "svc-builder"
    assert "storage" in data


def test_list_workflows(client):
    """Test listing workflows."""
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    data = response.json()
    assert "workflows" in data
    assert "total_count" in data
    assert "storage_stats" in data
    # Should have sample workflows loaded
    assert data["total_count"] >= 3


def test_get_workflow(client):
    """Test getting a specific workflow."""
    # Test with sample workflow
    response = client.get("/api/v1/workflows/wf_incidentes")
    assert response.status_code == 200
    data = response.json()
    assert data["spec_id"] == "wf_incidentes"
    assert "workflow_spec" in data
    assert data["workflow_spec"]["name"] == "Gestión de Incidentes"


def test_get_nonexistent_workflow(client):
    """Test getting a workflow that doesn't exist."""
    response = client.get("/api/v1/workflows/nonexistent")
    assert response.status_code == 404


def test_create_workflow(client):
    """Test creating a new workflow."""
    new_workflow = {
        "workflow_spec": {
            "specId": "test_workflow",
            "specVersion": 1,
            "tenantId": "test_tenant",
            "name": "Test Workflow",
            "slug": "test_workflow",
            "states": [
                {"slug": "start", "name": "Start", "type": "initial"},
                {"slug": "end", "name": "End", "type": "final"}
            ],
            "actions": [
                {
                    "slug": "finish",
                    "from": "start",
                    "to": "end",
                    "requiresForm": False,
                    "permission": "finish_task"
                }
            ],
            "permissions": [{"slug": "finish_task"}],
            "automations": []
        }
    }

    response = client.post("/api/v1/workflows", json=new_workflow)
    assert response.status_code == 201
    data = response.json()
    assert data["spec_id"] == "test_workflow"

    # Clean up - delete the test workflow
    client.delete("/api/v1/workflows/test_workflow")


def test_update_workflow(client):
    """Test updating an existing workflow."""
    # First create a workflow
    new_workflow = {
        "workflow_spec": {
            "specId": "update_test",
            "specVersion": 1,
            "tenantId": "test_tenant",
            "name": "Update Test",
            "slug": "update_test",
            "states": [
                {"slug": "start", "name": "Start", "type": "initial"}
            ],
            "actions": [],
            "permissions": [],
            "automations": []
        }
    }

    # Create
    create_response = client.post("/api/v1/workflows", json=new_workflow)
    assert create_response.status_code == 201

    # Update
    updated_workflow = {
        "workflow_spec": {
            "specId": "update_test",
            "specVersion": 2,
            "tenantId": "test_tenant",
            "name": "Updated Test",
            "slug": "update_test",
            "states": [
                {"slug": "start", "name": "Start", "type": "initial"},
                {"slug": "end", "name": "End", "type": "final"}
            ],
            "actions": [],
            "permissions": [],
            "automations": []
        }
    }

    update_response = client.put("/api/v1/workflows/update_test", json=updated_workflow)
    assert update_response.status_code == 200

    # Verify update
    get_response = client.get("/api/v1/workflows/update_test")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["workflow_spec"]["name"] == "Updated Test"
    assert data["workflow_spec"]["specVersion"] == 2

    # Clean up
    client.delete("/api/v1/workflows/update_test")


def test_delete_workflow(client):
    """Test deleting a workflow."""
    # First create a workflow to delete
    new_workflow = {
        "workflow_spec": {
            "specId": "delete_test",
            "specVersion": 1,
            "tenantId": "test_tenant",
            "name": "Delete Test",
            "slug": "delete_test",
            "states": [
                {"slug": "start", "name": "Start", "type": "initial"}
            ],
            "actions": [],
            "permissions": [],
            "automations": []
        }
    }

    # Create
    create_response = client.post("/api/v1/workflows", json=new_workflow)
    assert create_response.status_code == 201

    # Delete
    delete_response = client.delete("/api/v1/workflows/delete_test")
    assert delete_response.status_code == 200

    # Verify deletion
    get_response = client.get("/api/v1/workflows/delete_test")
    assert get_response.status_code == 404


def test_validate_workflow(client):
    """Test workflow validation."""
    # Test validation of existing workflow
    response = client.post("/api/v1/workflows/wf_incidentes/validate")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["spec_id"] == "wf_incidentes"