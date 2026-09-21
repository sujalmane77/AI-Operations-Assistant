"""
Read/write helpers for conversation memory and execution logs.
"""
import json
from typing import Any
from app.memory.db import get_conn


def save_message(session_id: str, role: str, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()
    conn.close()


def get_recent_messages(session_id: str, n: int = 20) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT role, content, timestamp FROM conversations
        WHERE session_id = ?
        ORDER BY id DESC LIMIT ?
        """,
        (session_id, n),
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def save_log(
    session_id: str,
    step_type: str,
    name: str = "",
    input: Any = None,
    output: Any = None,
    status: str = "ok",
    duration_ms: int = 0,
):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO execution_logs
        (session_id, step_type, name, input, output, status, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            step_type,
            name,
            json.dumps(input, default=str) if input is not None else None,
            json.dumps(output, default=str) if output is not None else None,
            status,
            duration_ms,
        ),
    )
    conn.commit()
    conn.close()


def get_logs(session_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT step_type, name, input, output, status, duration_ms, timestamp
        FROM execution_logs WHERE session_id = ? ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
