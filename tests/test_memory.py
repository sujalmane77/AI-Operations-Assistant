import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory.db import init_db
from app.memory.memory_store import save_message, get_recent_messages, save_log, get_logs


def test_message_roundtrip():
    init_db()
    sid = "test-session-mem"
    save_message(sid, "user", "hello world")
    msgs = get_recent_messages(sid, n=5)
    assert any(m["content"] == "hello world" and m["role"] == "user" for m in msgs)


def test_log_roundtrip():
    init_db()
    sid = "test-session-log"
    save_log(sid, "tool_call", name="dummy_tool", input={"a": 1}, output={"ok": True}, status="ok", duration_ms=10)
    logs = get_logs(sid)
    assert any(l["name"] == "dummy_tool" and l["status"] == "ok" for l in logs)


if __name__ == "__main__":
    test_message_roundtrip()
    test_log_roundtrip()
    print("test_memory.py: all tests passed")
