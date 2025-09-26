import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.main import app
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from shared.schemas import ChatRequest, WorkflowSpec


# Sample workflow for testing
SAMPLE_WORKFLOW_DATA = {
    "specId": "wf_incidentes",
    "specVersion": 1,
    "tenantId": "luke_123",
    "name": "Gestión de Incidentes",
    "slug": "gestion_incidentes",
    "states": [
        {"slug": "reportado", "name": "Incidente reportado", "type": "initial"},
        {"slug": "en_resolucion", "name": "En resolución", "type": "intermediate"},
        {"slug": "resuelto", "name": "Resuelto", "type": "final"}
    ],
    "actions": [
        {
            "slug": "pasar_a_resolucion",
            "from": "reportado",
            "to": "en_resolucion",
            "requiresForm": False,
            "permission": "pasar_a_resolucion"
        }
    ],
    "permissions": [
        {"slug": "pasar_a_resolucion"}
    ],
    "automations": []
}


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test the health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "mcp_server_connected" in data


@pytest.mark.asyncio
async def test_chat_endpoint():
    """Test the chat endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        chat_request = {
            "message": "What is this workflow about?",
            "workflow_spec": SAMPLE_WORKFLOW_DATA
        }

        response = await ac.post("/api/v1/chat", json=chat_request)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert "prompt_count" in data
        assert "mcp_tools_used" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0


@pytest.mark.asyncio
async def test_chat_without_workflow():
    """Test chat endpoint without workflow specification."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        chat_request = {
            "message": "Hello, can you help me?"
        }

        response = await ac.post("/api/v1/chat", json=chat_request)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)


@pytest.mark.asyncio
async def test_conversation_continuity():
    """Test that conversations maintain continuity."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First message
        chat_request1 = {
            "message": "What states does this workflow have?",
            "workflow_spec": SAMPLE_WORKFLOW_DATA
        }

        response1 = await ac.post("/api/v1/chat", json=chat_request1)
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]

        # Follow-up message with same conversation ID
        chat_request2 = {
            "message": "What about the actions?",
            "workflow_spec": SAMPLE_WORKFLOW_DATA,
            "conversation_id": conversation_id
        }

        response2 = await ac.post("/api/v1/chat", json=chat_request2)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["conversation_id"] == conversation_id
        assert data2["prompt_count"] == 2


@pytest.mark.asyncio
async def test_conversation_history():
    """Test getting conversation history."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a conversation
        chat_request = {
            "message": "What is this workflow about?",
            "workflow_spec": SAMPLE_WORKFLOW_DATA
        }

        chat_response = await ac.post("/api/v1/chat", json=chat_request)
        conversation_id = chat_response.json()["conversation_id"]

        # Get history
        history_response = await ac.get(f"/api/v1/conversations/{conversation_id}/history")
        assert history_response.status_code == 200

        history_data = history_response.json()
        assert "conversation_id" in history_data
        assert "total_turns" in history_data
        assert "history" in history_data
        assert history_data["total_turns"] == 1


@pytest.mark.asyncio
async def test_clear_conversation():
    """Test clearing conversation history."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Start a conversation
        chat_request = {
            "message": "Hello",
            "workflow_spec": SAMPLE_WORKFLOW_DATA
        }

        chat_response = await ac.post("/api/v1/chat", json=chat_request)
        conversation_id = chat_response.json()["conversation_id"]

        # Clear conversation
        clear_response = await ac.delete(f"/api/v1/conversations/{conversation_id}")
        assert clear_response.status_code == 200

        # Verify it's cleared
        history_response = await ac.get(f"/api/v1/conversations/{conversation_id}/history")
        history_data = history_response.json()
        assert history_data["total_turns"] == 0


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data