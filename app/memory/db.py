"""
SQLite schema + connection handling.
Plain sqlite3, no ORM, for transparency.
"""
import sqlite3
import os
from app.config import config


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.sqlite_db) or ".", exist_ok=True)
    conn = sqlite3.connect(config.sqlite_db)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            step_type TEXT NOT NULL,  -- retrieval / tool_call / decision / error
            name TEXT,
            input TEXT,
            output TEXT,
            status TEXT,
            duration_ms INTEGER,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Mock "company database" used by the search_database tool.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            assignee TEXT NOT NULL,
            priority TEXT NOT NULL
        )
    """)

    cur.execute("SELECT COUNT(*) FROM company_tickets")
    if cur.fetchone()[0] == 0:
        seed = [
            ("VPN access request - new hire", "open", "IT Support", "medium"),
            ("Laptop replacement - battery issue", "in_progress", "IT Support", "high"),
            ("Payroll discrepancy - September", "open", "Finance Ops", "high"),
            ("Onboarding checklist - Sujal R.", "closed", "HR", "low"),
            ("Client meeting room booking conflict", "open", "Facilities", "medium"),
        ]
        cur.executemany(
            "INSERT INTO company_tickets (title, status, assignee, priority) VALUES (?, ?, ?, ?)",
            seed,
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at {config.sqlite_db}")
