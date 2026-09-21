import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.memory.db import init_db
from app.tools import search_documents, search_database, create_summary, dummy_echo_tool  # noqa: F401 - registers tools
from app.tools.base import TOOL_REGISTRY


def test_search_documents_tool():
    tool = TOOL_REGISTRY["search_documents"]
    result = tool.run(query="What healthcare solutions does Wadhwani AI provide?")
    assert "results" in result
    assert len(result["results"]) > 0
    assert "text" in result["results"][0] and "source_section" in result["results"][0]


def test_search_database_tool():
    init_db()
    tool = TOOL_REGISTRY["search_database"]
    result = tool.run(status="open")
    assert "results" in result


def test_create_summary_tool():
    tool = TOOL_REGISTRY["create_summary"]
    result = tool.run(text="Wadhwani AI is a nonprofit that builds AI for healthcare, education and agriculture.")
    assert "summary" in result and len(result["summary"]) > 0


def test_new_tool_registers_with_no_other_file_edits():
    """Adding app/tools/dummy_echo_tool.py alone (no edits elsewhere) registers it."""
    assert "dummy_echo" in TOOL_REGISTRY
    result = TOOL_REGISTRY["dummy_echo"].run(text="hello")
    assert result == {"echoed": "hello"}


if __name__ == "__main__":
    test_search_documents_tool()
    test_search_database_tool()
    test_create_summary_tool()
    test_new_tool_registers_with_no_other_file_edits()
    print("test_tools.py: passed")
