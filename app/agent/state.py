from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    session_id: str
    user_message: str
    messages: list[dict]           # running conversation for LLM context
    retrieved_context: list[dict]  # chunks from search_documents, if any
    planned_action: dict           # last planner decision
    tool_result: Any               # last tool's output
    final_answer: str
    step_count: int
    max_steps: int
    trace: list[dict]              # human-readable step-by-step trace for the API/UI
    done: bool
