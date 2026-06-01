from uuid import uuid4
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from main import run_pipeline
from core.rag_engine import ask_question


app = FastAPI(title="Video RAG API", version="0.1.0")

# In-memory session store (simple, minimal approach)
SESSIONS: Dict[str, Dict[str, Any]] = {}


class PipelineRequest(BaseModel):
    source: str = Field(..., description="YouTube URL or local file path")
    language: str = Field(default="english", description="english or hinglish")


class ChatRequest(BaseModel):
    session_id: str
    question: str


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/pipeline")
def create_pipeline(req: PipelineRequest) -> Dict[str, Any]:
    result = run_pipeline(req.source, req.language)

    session_id = str(uuid4())
    rag_chain = result["rag_chain"]

    # Keep chain and short-term history in memory for chat follow-ups.
    SESSIONS[session_id] = {"rag_chain": rag_chain, "chat_history": []}

    # Return JSON-safe payload (omit rag_chain object)
    return {
        "session_id": session_id,
        "title": result["title"],
        "transcript": result["transcript"],
        "summary": result["summary"],
        "action_items": result["action_items"],
        "key_decisions": result["key_decisions"],
        "open_questions": result["open_questions"],
    }


@app.post("/chat")
def chat(req: ChatRequest) -> Dict[str, str]:
    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    rag_chain = session["rag_chain"]
    chat_history: List[Dict[str, str]] = session["chat_history"]

    chat_history.append({"role": "user", "text": req.question})

    recent = chat_history[-6:]
    extra_context = "\n".join(
        f"{h['role'].capitalize()}: {h['text']}" for h in recent
    )

    answer = ask_question(rag_chain, req.question, extra_context=extra_context)

    chat_history.append({"role": "assistant", "text": answer})

    return {"answer": answer}
