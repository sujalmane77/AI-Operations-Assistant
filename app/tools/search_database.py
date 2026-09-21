"""
Queries the mock 'company_tickets' table seeded in app/memory/db.py.
Supports simple filtering by status/assignee/priority/title keyword.
"""
from app.tools.base import register_tool
from app.memory.db import get_conn


@register_tool(
    name="search_database",
    description=(
        "Search the internal company ticket database. Can filter by status "
        "(open/in_progress/closed), assignee, priority (low/medium/high), "
        "or a keyword in the title."
    ),
    input_schema={
        "status": "optional: open | in_progress | closed",
        "assignee": "optional: team/person name",
        "priority": "optional: low | medium | high",
        "keyword": "optional: keyword to match in the ticket title",
    },
)
def search_database(status: str = None, assignee: str = None, priority: str = None, keyword: str = None) -> dict:
    conn = get_conn()
    query = "SELECT id, title, status, assignee, priority FROM company_tickets WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if assignee:
        query += " AND assignee LIKE ?"
        params.append(f"%{assignee}%")
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if keyword:
        query += " AND title LIKE ?"
        params.append(f"%{keyword}%")

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {"results": [dict(r) for r in rows], "count": len(rows)}
