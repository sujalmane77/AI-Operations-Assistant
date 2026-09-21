"""
Proves the tool registry is extensible with zero edits to any other file:
adding this one file registers a new tool automatically via the decorator.
"""
from app.tools.base import register_tool


@register_tool(
    name="dummy_echo",
    description="Test-only tool that echoes its input back.",
    input_schema={"text": "text to echo"},
)
def dummy_echo(text: str) -> dict:
    return {"echoed": text}
