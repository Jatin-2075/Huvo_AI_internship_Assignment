import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Must run before anything that reads env vars at import time (app.llm builds
# the Gemini client as soon as it's imported).
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.analytics import generate_analytics
from app.llm import get_agent_reply

app = FastAPI(title="Northstar Homes AI Sales Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- In-memory session store -------------------------------------------------
# {session_id: {"messages": [Gemini-format {"role", "parts"} messages], "ended": bool, "analytics": dict|None}}
SESSIONS: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class EndRequest(BaseModel):
    session_id: str


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    session = SESSIONS.setdefault(session_id, {"messages": [], "ended": False, "analytics": None})

    if session["ended"]:
        raise HTTPException(400, "This conversation has ended. Start a new session.")

    session["messages"].append({"role": "user", "parts": [{"text": req.message}]})

    try:
        reply_text, updated_history = get_agent_reply(session["messages"])
    except Exception as exc:  # surfaces missing/invalid API key etc. clearly to the UI
        raise HTTPException(500, f"LLM call failed: {exc}") from exc

    session["messages"] = updated_history
    return ChatResponse(session_id=session_id, reply=reply_text)


@app.post("/api/end")
def end_conversation(req: EndRequest):
    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(404, "Unknown session_id")

    session["ended"] = True

    transcript_lines = []
    for msg in session["messages"]:
        role = msg["role"]
        parts = msg["parts"]
        for part in parts:
            # Dicts like {"text": ...} (our own appended user turns) or
            # Gemini Part objects (model turns) with a .text attribute.
            text = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
            if text:
                transcript_lines.append(f"{role}: {text}")
    transcript_text = "\n".join(transcript_lines)

    analytics = generate_analytics(transcript_text)
    session["analytics"] = analytics
    return {"session_id": req.session_id, "analytics": analytics}


@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Unknown session_id")
    return {
        "ended": session["ended"],
        "analytics": session["analytics"],
        "message_count": len(session["messages"]),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)