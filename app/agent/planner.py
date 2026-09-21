"""
Planner node: given current state, decides the next action as JSON:
  {"action": "retrieve_more" | "call_tool" | "respond_final",
   "tool_name": "...", "tool_args": {...},   # only if action == call_tool
   "final_answer": "..."}                     # only if action == respond_final
"""
import json
import re

from app.agent.llm import call_llm
from app.agent.system_prompt import SYSTEM_PROMPT
from app.tools.base import list_tools_for_prompt


PLANNER_INSTRUCTIONS = """Below is the user's question and everything gathered so far while \
answering it. Decide exactly ONE next action.

User's question (this is what you must ultimately answer):
{history}

Available tools:
{tools}

Retrieved company knowledge so far (may be empty):
{context}

Last tool result (may be empty):
{tool_result}

Respond with ONLY a JSON object, no prose, no markdown fences, matching one of these shapes:

1. To search the knowledge base:
{{"action": "call_tool", "tool_name": "search_documents", "tool_args": {{"query": "..."}}}}

2. To use any other tool:
{{"action": "call_tool", "tool_name": "<tool_name>", "tool_args": {{...}}}}

3. To finish and answer the user's question above directly, using the retrieved knowledge \
(only once you have enough information, or if no tool/retrieval is needed at all, or if the \
knowledge base clearly doesn't cover this):
{{"action": "respond_final", "final_answer": "..."}}

Rules:
- If the user's question needs company knowledge and you haven't retrieved it yet, call \
search_documents first.
- Don't call the same tool with the same arguments twice.
- If retrieval came back empty/irrelevant, don't keep retrying — respond_final honestly \
saying the knowledge base doesn't cover it.
- final_answer must never be empty, must never ask the user for "more context" if the \
retrieved knowledge above already answers their question, and must directly address the \
user's question shown above — not describe the planning process itself.
- Respond with raw JSON only.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Planner did not return JSON: {text!r}")
    return json.loads(match.group(0))


def plan_next_step(state: dict) -> dict:
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in state.get("messages", []))
    context_text = "\n".join(
        f"[{c['source_section']}] {c['text'][:300]}" for c in state.get("retrieved_context", [])
    ) or "(none yet)"
    tool_result_text = json.dumps(state.get("tool_result"), default=str) if state.get("tool_result") else "(none yet)"

    prompt = PLANNER_INSTRUCTIONS.format(
        tools=list_tools_for_prompt(),
        history=history_text,
        context=context_text,
        tool_result=tool_result_text,
    )

    raw = call_llm(messages=[{"role": "user", "content": prompt}], system_prompt=SYSTEM_PROMPT)

    try:
        return _extract_json(raw)
    except Exception:
        # If the planner ever fails to produce parseable JSON, fail safe
        # into a final response rather than crashing the graph.
        return {"action": "respond_final", "final_answer": raw}
