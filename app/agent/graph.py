"""
LangGraph StateGraph implementing:
  intent -> retrieve (conditional) -> reason -> tool (conditional) -> observe
  -> loops back to reason until planner says respond_final or max_steps hit
  -> final (writes memory + logs)
"""
import time

from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.planner import plan_next_step
from app.agent.llm import call_llm
from app.agent.system_prompt import SYSTEM_PROMPT
from app.tools.base import TOOL_REGISTRY
from app.memory.memory_store import save_message
from app.logging.logger import log_step
from app.config import config

# Import tool modules so their @register_tool decorators run and populate TOOL_REGISTRY.
from app.tools import search_documents, search_database, create_summary, send_email, schedule_meeting  # noqa: F401


def intent_node(state: AgentState) -> AgentState:
    state.setdefault("messages", [{"role": "user", "content": state["user_message"]}])
    state.setdefault("retrieved_context", [])
    state.setdefault("trace", [])
    state.setdefault("step_count", 0)
    state.setdefault("max_steps", config.agent_max_steps)
    state.setdefault("done", False)

    with log_step(state["session_id"], "decision", "intent_node", input=state["user_message"]) as finish:
        finish(output="intent captured", status="ok")

    state["trace"].append({"step": "intent", "detail": state["user_message"]})
    return state


def reason_node(state: AgentState) -> AgentState:
    state["step_count"] += 1

    with log_step(state["session_id"], "decision", "planner", input={"step": state["step_count"]}) as finish:
        decision = plan_next_step(state)
        finish(output=decision, status="ok")

    if decision.get("action") == "respond_final" and not (decision.get("final_answer") or "").strip():
        # The LLM occasionally returns valid JSON with a blank final_answer.
        # Give it one more chance before falling back to a clear message
        # instead of silently returning an empty answer.
        with log_step(state["session_id"], "decision", "planner_retry", input={"step": state["step_count"]}) as finish:
            retry = plan_next_step(state)
            finish(output=retry, status="ok")
        if retry.get("action") == "respond_final" and (retry.get("final_answer") or "").strip():
            decision = retry
        elif retry.get("action") != "respond_final":
            decision = retry
        else:
            decision = {
                "action": "respond_final",
                "final_answer": "I wasn't able to compose a complete answer for this request. "
                                 "Please try rephrasing your question.",
            }

    state["planned_action"] = decision
    state["trace"].append({"step": "reason", "decision": decision})

    if decision.get("action") == "respond_final" or state["step_count"] >= state["max_steps"]:
        if state["step_count"] >= state["max_steps"] and decision.get("action") != "respond_final":
            decision = {
                "action": "respond_final",
                "final_answer": "I wasn't able to fully complete this within the allotted "
                                 "reasoning steps. Here's what I found so far, but you may "
                                 "want to rephrase or narrow the request.",
            }
            state["planned_action"] = decision
        state["final_answer"] = decision.get("final_answer", "")
        state["done"] = True

    return state


def tool_node(state: AgentState) -> AgentState:
    decision = state["planned_action"]
    tool_name = decision.get("tool_name")
    tool_args = decision.get("tool_args", {}) or {}

    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        result = {"error": f"Unknown tool '{tool_name}'"}
        status = "error"
        with log_step(state["session_id"], "tool_call", tool_name or "unknown", input=tool_args) as finish:
            finish(output=result, status="error")
    else:
        max_retries = 2
        last_error = None
        result = None
        status = "error"
        for attempt in range(max_retries + 1):
            try:
                with log_step(state["session_id"], "tool_call", tool_name, input=tool_args) as finish:
                    result = tool.run(**tool_args)
                    finish(output=result, status="ok")
                status = "ok"
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        if status == "error":
            result = {
                "error": f"Tool '{tool_name}' failed after {max_retries + 1} attempt(s): {last_error}"
            }

    state["tool_result"] = result
    state["trace"].append({"step": "tool_call", "tool": tool_name, "args": tool_args, "result": result, "status": status})

    if tool_name == "search_documents" and isinstance(result, dict) and "results" in result:
        state["retrieved_context"].extend(result["results"])
        with log_step(state["session_id"], "retrieval", "search_documents", input=tool_args) as finish:
            finish(output=result["results"], status="ok")

    return state


def observe_node(state: AgentState) -> AgentState:
    # Fold the tool result back into the conversation so the next reasoning
    # pass has it as context. Truncated: search_documents' full text already
    # lives in retrieved_context, and messages accumulate every loop step,
    # so leaving this unbounded eventually blows past the LLM's payload
    # limit on multi-step queries.
    tool_name = state["planned_action"].get("tool_name")
    result_text = str(state["tool_result"])
    if tool_name == "search_documents":
        result_text = f"(retrieved {len(state['tool_result'].get('results', []))} chunk(s), see context above)"
    elif len(result_text) > 500:
        result_text = result_text[:500] + "...(truncated)"
    state["messages"].append({
        "role": "assistant",
        "content": f"(internal) tool '{tool_name}' returned: {result_text}",
    })
    state["trace"].append({"step": "observe", "tool_result": state["tool_result"]})
    return state


def final_node(state: AgentState) -> AgentState:
    save_message(state["session_id"], "user", state["user_message"])
    save_message(state["session_id"], "assistant", state["final_answer"])
    with log_step(state["session_id"], "decision", "final_answer", input=None) as finish:
        finish(output=state["final_answer"], status="ok")
    return state


def _route_after_reason(state: AgentState) -> str:
    if state.get("done"):
        return "final"
    return "tool"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("intent", intent_node)
    graph.add_node("reason", reason_node)
    graph.add_node("tool", tool_node)
    graph.add_node("observe", observe_node)
    graph.add_node("final", final_node)

    graph.set_entry_point("intent")
    graph.add_edge("intent", "reason")
    graph.add_conditional_edges("reason", _route_after_reason, {"tool": "tool", "final": "final"})
    graph.add_edge("tool", "observe")
    graph.add_edge("observe", "reason")
    graph.add_edge("final", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_agent(session_id: str, user_message: str) -> dict:
    graph = get_compiled_graph()
    initial_state: AgentState = {"session_id": session_id, "user_message": user_message}
    final_state = graph.invoke(initial_state)
    return {"final_answer": final_state.get("final_answer", ""), "trace": final_state.get("trace", [])}
