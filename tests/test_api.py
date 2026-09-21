import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_chat_rag_question():
    resp = client.post("/chat", json={
        "session_id": "test-api-session",
        "message": "What healthcare solutions does Wadhwani AI provide?",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert isinstance(body["steps"], list) and len(body["steps"]) > 0


def test_session_history_and_logs():
    history = client.get("/sessions/test-api-session/history")
    assert history.status_code == 200
    assert any(m["role"] == "user" for m in history.json())

    logs = client.get("/sessions/test-api-session/logs")
    assert logs.status_code == 200
    assert len(logs.json()) > 0


if __name__ == "__main__":
    test_health()
    test_chat_rag_question()
    test_session_history_and_logs()
    print("test_api.py: passed")
