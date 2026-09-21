"""
Tool base class + self-registering registry. New tools should only need
to add a file here that imports `register_tool` — no other file needs
to change.
"""
from dataclasses import dataclass, field
from typing import Callable, Any

TOOL_REGISTRY: dict[str, "Tool"] = {}


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict  # {"param_name": "description"} — kept simple/human-readable
    run: Callable[..., Any]


def register_tool(name: str, description: str, input_schema: dict):
    """
    Decorator: wraps a function as a Tool and adds it to TOOL_REGISTRY.

    Usage:
        @register_tool(
            name="search_documents",
            description="...",
            input_schema={"query": "the search query"},
        )
        def search_documents(query: str) -> dict:
            ...
    """
    def decorator(fn: Callable[..., Any]):
        TOOL_REGISTRY[name] = Tool(
            name=name, description=description, input_schema=input_schema, run=fn
        )
        return fn
    return decorator


def list_tools_for_prompt() -> str:
    """Human-readable tool list, used inside the planner's LLM prompt."""
    lines = []
    for tool in TOOL_REGISTRY.values():
        params = ", ".join(f"{k} ({v})" for k, v in tool.input_schema.items())
        lines.append(f"- {tool.name}({params}): {tool.description}")
    return "\n".join(lines)
