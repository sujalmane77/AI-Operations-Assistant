"""
CLI: python scripts/run_agent.py "<your query>" [session_id]
"""
import sys
import json
import uuid

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.memory.db import init_db
from app.agent.graph import run_agent


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/run_agent.py "your query" [session_id]')
        sys.exit(1)

    query = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else str(uuid.uuid4())[:8]

    init_db()
    result = run_agent(session_id=session_id, user_message=query)

    print("\n=== FINAL ANSWER ===")
    print(result["final_answer"])

    print("\n=== TRACE ===")
    for step in result["trace"]:
        print(json.dumps(step, indent=2, default=str))

    print(f"\n(session_id: {session_id})")


if __name__ == "__main__":
    main()
