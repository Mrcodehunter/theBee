"""
server.py — FastAPI backend that exposes the LangGraph agent (agent_graph.py)
to the web UI (../ui).

Endpoints:
    GET    /api/health
    POST   /api/sessions                    create a new chat session
    GET    /api/sessions                    list sessions
    DELETE /api/sessions/{id}                drop a session
    GET    /api/sessions/{id}/messages       full message history (+ pending approval, if any)
    POST   /api/sessions/{id}/messages       send a user message -> SSE stream of agent events
    POST   /api/sessions/{id}/approve        answer a pending approval -> SSE stream of agent events
    POST   /api/sessions/{id}/upload         save an image into the sandbox, returns its path

One graph instance is built at startup for PROJECT_DIR; each chat session is
just a distinct `thread_id` into that graph's checkpointer, so conversation
history and human-in-the-loop approvals are handled entirely by LangGraph.

Run:
    uvicorn server:app --reload --port 8000
    (optionally set AGENT_PROJECT_DIR to point the agent at a project, and
    ANTHROPIC_API_KEY to enable Claude — both can also go in agent/.env)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

load_dotenv()  # load agent/.env, if present, before reading any env vars below

from agent_graph import build_graph, MODEL_NAME
from models import DEFAULT_MODEL_ID, is_available, list_models
from tools.image_tools import SUPPORTED_IMAGE_TYPES

MAX_ITERATIONS = 15
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Project sandbox + graph (built once, shared by every session)
# ---------------------------------------------------------------------------

PROJECT_DIR = Path(os.environ.get("AGENT_PROJECT_DIR", Path(__file__).resolve().parent.parent)).resolve()
if not PROJECT_DIR.is_dir():
    raise SystemExit(f"AGENT_PROJECT_DIR not found: {PROJECT_DIR}")

agent = build_graph(PROJECT_DIR)

# session_id -> {id, title, created_at}. Conversation state itself lives in
# the graph's checkpointer, keyed by the same session_id as thread_id.
SESSIONS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Dev Agent API")

app.add_middleware(
    CORSMiddleware,
    # Vite falls back to 5174/5175/... if 5173 is already taken by another
    # instance, so allow the whole local dev range rather than just 5173.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):517\d",
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateSessionBody(BaseModel):
    title: Optional[str] = None


class MessageBody(BaseModel):
    content: str
    model: Optional[str] = None


class ApproveBody(BaseModel):
    approved: bool
    model: Optional[str] = None


def _config(session_id: str, model_id: str = DEFAULT_MODEL_ID) -> dict:
    return {
        "configurable": {"thread_id": session_id, "model_id": model_id},
        "recursion_limit": MAX_ITERATIONS * 2,
    }


def _resolve_model(model_id: Optional[str]) -> str:
    """Validate the requested model id, defaulting to the local model.
    Raises a 400 (rather than letting a missing API key blow up mid-stream)
    if the caller asked for a model that isn't configured."""
    if model_id is None:
        return DEFAULT_MODEL_ID
    if not is_available(model_id):
        raise HTTPException(status_code=400, detail=f"Model '{model_id}' is not available on this server")
    return model_id


def _require_session(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _serialize_messages(messages: list) -> list[dict]:
    out = []
    for msg in messages:
        msg_type = getattr(msg, "type", "")
        if msg_type == "human":
            out.append({"role": "user", "content": msg.text})
        elif msg_type == "ai":
            # msg.content can be a plain string or a list of content blocks
            # (e.g. {"type": "text", "text": "...", "index": 0}) depending on
            # the model backend — .text normalizes either shape to a string.
            entry = {"role": "assistant", "content": msg.text or ""}
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                entry["tool_calls"] = [{"name": c["name"], "args": c["args"]} for c in tool_calls]
            out.append(entry)
        elif msg_type == "tool":
            out.append({
                "role": "tool",
                "name": getattr(msg, "name", ""),
                "content": msg.text[:2000],
            })
    return out


def _pending_interrupt(session_id: str):
    state = agent.get_state(_config(session_id))
    for task in state.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "project_dir": str(PROJECT_DIR), "model": MODEL_NAME}


@app.get("/api/models")
def get_models():
    return list_models()


@app.post("/api/sessions")
def create_session(body: CreateSessionBody):
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "title": body.title or "New chat",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    SESSIONS[session_id] = session
    return session


@app.get("/api/sessions")
def list_sessions():
    return sorted(SESSIONS.values(), key=lambda s: s["created_at"], reverse=True)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    _require_session(session_id)
    del SESSIONS[session_id]
    return {"ok": True}


@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: str):
    _require_session(session_id)
    state = agent.get_state(_config(session_id))
    messages = state.values.get("messages", []) if state.values else []
    return {
        "messages": _serialize_messages(messages),
        "pending_interrupt": _pending_interrupt(session_id),
    }


@app.post("/api/sessions/{session_id}/upload")
async def upload_image(session_id: str, file: UploadFile):
    """Save an uploaded image into the sandboxed project directory and
    return its relative path, in the same form analyze_image expects. This
    is a direct human action (the user deliberately attaching a file), not
    an agent tool call, so it doesn't go through the approval gate agent-
    initiated actions do."""
    _require_session(session_id)

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{suffix}'. Supported: {', '.join(SUPPORTED_IMAGE_TYPES)}",
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"Image exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")

    uploads_dir = PROJECT_DIR / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    name = f"{uuid.uuid4().hex}{suffix}"
    (uploads_dir / name).write_bytes(data)

    return {"path": f"uploads/{name}"}


# ---------------------------------------------------------------------------
# Streaming chat + approval
# ---------------------------------------------------------------------------

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream_run(session_id: str, run_input, model_id: str) -> "StreamingResponse":
    config = _config(session_id, model_id)

    def gen():
        try:
            hit_interrupt = False
            for mode, chunk in agent.stream(run_input, config=config, stream_mode=["updates", "messages"]):
                if mode == "messages":
                    message_chunk, metadata = chunk
                    # .content may be a plain string or a list of content
                    # blocks (e.g. {"type": "text", "text": "...", "index": 0})
                    # depending on the model backend; .text normalizes either
                    # shape to a string and is what the UI expects.
                    if metadata.get("langgraph_node") == "agent" and message_chunk.text:
                        yield _sse("token", {"content": message_chunk.text})
                elif mode == "updates":
                    for node, update in chunk.items():
                        if node == "__interrupt__":
                            hit_interrupt = True
                            yield _sse("approval_request", update[0].value)
                        elif node == "agent":
                            msg = update["messages"][-1]
                            tool_calls = getattr(msg, "tool_calls", None)
                            if tool_calls:
                                for call in tool_calls:
                                    yield _sse("tool_call", {"name": call["name"], "args": call["args"]})
                        elif node == "tools":
                            for msg in update["messages"]:
                                yield _sse("tool_result", {
                                    "name": getattr(msg, "name", ""),
                                    "content": msg.text[:2000],
                                })
            if not hit_interrupt:
                # First message becomes the session title, ChatGPT-style.
                session = SESSIONS.get(session_id)
                if session is not None and session["title"] == "New chat":
                    state = agent.get_state(config)
                    for msg in state.values.get("messages", []):
                        if getattr(msg, "type", "") == "human":
                            session["title"] = (msg.content or "New chat")[:60]
                            break
                yield _sse("done", {})
        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/sessions/{session_id}/messages")
def post_message(session_id: str, body: MessageBody):
    _require_session(session_id)
    model_id = _resolve_model(body.model)
    run_input = {"messages": [{"role": "user", "content": body.content}]}
    return _stream_run(session_id, run_input, model_id)


@app.post("/api/sessions/{session_id}/approve")
def post_approve(session_id: str, body: ApproveBody):
    _require_session(session_id)
    model_id = _resolve_model(body.model)
    return _stream_run(session_id, Command(resume=body.approved), model_id)
