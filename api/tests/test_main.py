from fastapi.testclient import TestClient
from index import app


def test_health_check_returns_200():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "mcp_tools" in data


def test_chat_endpoint_empty_messages():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": []})
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"].lower()
