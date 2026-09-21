"""FastAPI entrypoint: health check + chat/session endpoints."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.memory.db import init_db
from app.memory.memory_store import get_recent_messages, get_logs
from app.agent.graph import run_agent

app = FastAPI(title="AI Operations Assistant")

init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    steps: list[dict]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = run_agent(session_id=req.session_id, user_message=req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")
    return ChatResponse(answer=result["final_answer"], steps=result["trace"])


@app.get("/sessions/{session_id}/history")
def session_history(session_id: str) -> list[dict]:
    return get_recent_messages(session_id, n=1000)


@app.get("/sessions/{session_id}/logs")
def session_logs(session_id: str) -> list[dict]:
    return get_logs(session_id)
