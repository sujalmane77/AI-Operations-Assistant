from app.tools.base import register_tool
from app.rag.retriever import retrieve


@register_tool(
    name="search_documents",
    description="Search the company knowledge base (handbook) for relevant policy/process information.",
    input_schema={"query": "the natural-language question to search for"},
)
def search_documents(query: str, k: int = 4) -> dict:
    results = retrieve(query, k=k)
    return {"query": query, "results": results}
