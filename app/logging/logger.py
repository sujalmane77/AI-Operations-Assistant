"""
Thin structured-logging wrapper: prints to console AND persists to
SQLite via memory_store.save_log, so every step is both visible live
and queryable later per session_id.
"""
import time
import logging as pylogging
from contextlib import contextmanager
from app.memory.memory_store import save_log

pylogging.basicConfig(level=pylogging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = pylogging.getLogger("ai_ops_assistant")


@contextmanager
def log_step(session_id: str, step_type: str, name: str, input=None):
    """
    Usage:
        with log_step(session_id, "tool_call", "search_database", input=args) as finish:
            result = do_the_thing()
            finish(output=result, status="ok")
    """
    start = time.time()
    state = {"output": None, "status": "ok"}

    def finish(output=None, status="ok"):
        state["output"] = output
        state["status"] = status

    try:
        yield finish
    except Exception as e:
        state["status"] = "error"
        state["output"] = str(e)
        logger.error(f"[{step_type}] {name} failed: {e}")
        raise
    finally:
        duration_ms = int((time.time() - start) * 1000)
        logger.info(f"[{step_type}] {name} -> {state['status']} ({duration_ms}ms)")
        save_log(
            session_id=session_id,
            step_type=step_type,
            name=name,
            input=input,
            output=state["output"],
            status=state["status"],
            duration_ms=duration_ms,
        )
