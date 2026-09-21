from app.tools.base import register_tool
from app.agent.llm import call_llm
from app.agent.system_prompt import SYSTEM_PROMPT


@register_tool(
    name="create_summary",
    description="Summarize a block of text/context into a short, structured summary.",
    input_schema={"text": "the text/context to summarize"},
)
def create_summary(text: str) -> dict:
    prompt = f"Summarize the following into 3-5 concise bullet points:\n\n{text}"
    summary = call_llm(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=SYSTEM_PROMPT,
    )
    return {"summary": summary}
