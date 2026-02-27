import logging
import uuid
from datetime import datetime, timezone

from fastapi import (
    APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect,
)
from pydantic import BaseModel

from ..core.database import get_database
from ..core.security import get_current_user
from ..models.groq_chat import GroqChat
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory chat session store (rebuilt from DB on restart)
chat_sessions: dict[str, GroqChat] = {}


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_json(self, data: dict, session_id: str):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json(data)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class QuestionRequest(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# Helper: build / rebuild a GroqChat instance from a DB summary
# ---------------------------------------------------------------------------
async def _get_or_rebuild_groq(session_id: str, summary_id: str, db) -> GroqChat:
    groq_chat = chat_sessions.get(session_id)
    if groq_chat:
        return groq_chat

    summary = await db.summaries.find_one({"summary_id": summary_id})
    if not summary:
        raise HTTPException(404, detail={"code": "SUMMARY_NOT_FOUND", "message": "Associated summary not found."})

    groq_chat = GroqChat(settings.GROQ_API_KEY)
    groq_chat.set_context(
        transcript=summary.get("transcript", ""),
        summary=summary.get("text_summary", ""),
        video_info=summary.get("video_info", {}),
        key_points=summary.get("key_points", []),
    )
    chat_sessions[session_id] = groq_chat
    return groq_chat


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/session/start")
async def start_chat_session(
    summary_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Start (or resume) a chat session for a given summary."""
    try:
        db = await get_database()

        summary = await db.summaries.find_one({
            "summary_id": summary_id,
            "user_id": str(current_user["_id"]),
        })
        if not summary:
            raise HTTPException(404, detail={"code": "SUMMARY_NOT_FOUND", "message": "Summary not found."})

        # Return existing session if one already exists
        existing = await db.chat_sessions.find_one({
            "summary_id": summary_id,
            "user_id": str(current_user["_id"]),
        })
        if existing:
            return {"session_id": existing["session_id"], "messages": existing.get("messages", [])}

        session_id = str(uuid.uuid4())

        groq_chat = GroqChat(settings.GROQ_API_KEY)
        groq_chat.set_context(
            transcript=summary.get("transcript", ""),
            summary=summary.get("text_summary", ""),
            video_info=summary.get("video_info", {}),
            key_points=summary.get("key_points", []),
        )
        chat_sessions[session_id] = groq_chat

        await db.chat_sessions.insert_one({
            "session_id": session_id,
            "user_id": str(current_user["_id"]),
            "video_id": summary.get("video_id", ""),
            "summary_id": summary_id,
            "messages": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

        logger.info("Chat session created: %s", session_id)
        return {"session_id": session_id, "messages": []}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to start chat session: %s", e)
        raise HTTPException(500, detail={"code": "SESSION_CREATE_FAILED", "message": "Failed to create chat session."})


@router.post("/session/{session_id}/ask")
async def ask_question(
    session_id: str,
    body: QuestionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Ask a question in a chat session (question in POST body, not query string)."""
    try:
        db = await get_database()

        session = await db.chat_sessions.find_one({
            "session_id": session_id,
            "user_id": str(current_user["_id"]),
        })
        if not session:
            raise HTTPException(404, detail={"code": "SESSION_NOT_FOUND", "message": "Chat session not found."})

        groq_chat = await _get_or_rebuild_groq(session_id, session["summary_id"], db)
        answer = await groq_chat.ask_question(body.question)

        now = datetime.now(timezone.utc).isoformat()
        user_msg = {"role": "user",      "content": body.question, "timestamp": now}
        asst_msg = {"role": "assistant", "content": answer,        "timestamp": now}

        # Use $push to atomically append — no full-array read/replace
        await db.chat_sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": {"$each": [user_msg, asst_msg]}},
                "$set":  {"updated_at": datetime.now(timezone.utc)},
            },
        )

        return {"answer": answer}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat ask failed for session %s: %s", session_id, e)
        raise HTTPException(500, detail={"code": "CHAT_FAILED", "message": "Failed to get answer. Please try again."})


@router.get("/session/{session_id}/messages")
async def get_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve full message history for a session."""
    try:
        db = await get_database()
        session = await db.chat_sessions.find_one({
            "session_id": session_id,
            "user_id": str(current_user["_id"]),
        })
        if not session:
            raise HTTPException(404, detail={"code": "SESSION_NOT_FOUND", "message": "Chat session not found."})
        return {"messages": session.get("messages", [])}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch messages for session %s: %s", session_id, e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": "Failed to retrieve messages."})


# ---------------------------------------------------------------------------
# Authenticated WebSocket
# ---------------------------------------------------------------------------
@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str, token: str = ""):
    """
    Real-time chat over WebSocket.
    Pass the JWT access token as a query parameter: ?token=<access_token>
    """
    # ---------- authenticate BEFORE accept ----------
    from ..core.security import get_current_user_from_token
    user = await get_current_user_from_token(token)
    if user is None:
        await websocket.close(code=1008)  # Policy Violation
        return

    await manager.connect(websocket, session_id)
    logger.info("WebSocket connected: session=%s user=%s", session_id, str(user.get("_id", "")))

    try:
        db = await get_database()
        while True:
            data = await websocket.receive_json()
            question = data.get("question", "").strip()
            if not question:
                continue

            session = await db.chat_sessions.find_one({"session_id": session_id})
            if not session:
                await manager.send_json({"error": "Session not found"}, session_id)
                continue

            groq_chat = await _get_or_rebuild_groq(session_id, session["summary_id"], db)
            answer = await groq_chat.ask_question(question)

            now = datetime.now(timezone.utc).isoformat()
            await db.chat_sessions.update_one(
                {"session_id": session_id},
                {
                    "$push": {
                        "messages": {
                            "$each": [
                                {"role": "user",      "content": question, "timestamp": now},
                                {"role": "assistant", "content": answer,   "timestamp": now},
                            ]
                        }
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )

            await manager.send_json({"question": question, "answer": answer, "timestamp": now}, session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info("WebSocket disconnected: session=%s", session_id)
    except Exception as e:
        logger.exception("WebSocket error for session %s: %s", session_id, e)
        manager.disconnect(session_id)