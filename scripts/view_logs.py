"""
CLI: python scripts/view_logs.py <session_id>
Prints a clean chronological trace of every retrieval/tool_call/decision/error.
"""
import sys
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.memory.memory_store import get_logs


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/view_logs.py <session_id>")
        sys.exit(1)

    session_id = sys.argv[1]
    logs = get_logs(session_id)

    if not logs:
        print(f"No logs found for session '{session_id}'.")
        return

    for log in logs:
        print(f"[{log['timestamp']}] {log['step_type']:10} | {log['name'] or '-':20} | "
              f"status={log['status']:5} | {log['duration_ms']}ms")
        if log["input"]:
            print(f"    input:  {log['input']}")
        if log["output"]:
            out = log["output"]
            print(f"    output: {out[:300]}{'...' if len(out) > 300 else ''}")
        print()


if __name__ == "__main__":
    main()
