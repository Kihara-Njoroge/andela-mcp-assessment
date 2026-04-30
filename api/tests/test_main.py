from fastapi.testclient import TestClient

from index import app


def test_health_check_returns_200():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "mcp_tools" in data


def test_chat_rejects_empty_messages():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": []})
        assert response.status_code == 422


def test_chat_rejects_invalid_role():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "hacker", "content": "hello"}]},
        )
        assert response.status_code == 422
        assert "Invalid role" in response.text


def test_chat_rejects_empty_content():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "   "}]},
        )
        assert response.status_code == 422
        assert "empty" in response.text.lower()


def test_chat_rejects_oversized_content():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "x" * 2001}]},
        )
        assert response.status_code == 422
        assert "2000" in response.text


def test_chat_rejects_too_many_messages():
    with TestClient(app) as client:
        messages = [{"role": "user", "content": "hi"}] * 51
        response = client.post("/api/chat", json={"messages": messages})
        assert response.status_code == 422
        assert "50" in response.text


def test_chat_rejects_missing_fields():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [{"role": "user"}]})
        assert response.status_code == 422


def test_chat_rejects_invalid_json():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


def test_health_check_returns_correct_schema():
    with TestClient(app) as client:
        response = client.get("/api/health")
        data = response.json()
        assert isinstance(data["status"], str)
        assert isinstance(data["mcp_tools"], int)
        assert data["mcp_tools"] >= 0
