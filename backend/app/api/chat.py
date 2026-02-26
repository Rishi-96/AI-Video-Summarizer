from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Optional
import uuid
from datetime import datetime

from ..core.database import get_database
from ..core.security import get_current_user
from ..models.gemini_chat import GeminiChat
from ..core.config import settings

router = APIRouter()

# Store active chat sessions
chat_sessions = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()

@router.post("/session/start")
async def start_chat_session(summary_id: str):
    """Start a new chat session (no auth for testing)"""
    try:
        db = await get_database()
        
        # Get summary
        summary = await db.summaries.find_one({"summary_id": summary_id})
        
        if not summary:
            raise HTTPException(404, "Summary not found")
        
        # Check if session already exists
        existing_session = await db.chat_sessions.find_one({"summary_id": summary_id})
        
        if existing_session:
            return {
                "session_id": existing_session["session_id"],
                "messages": existing_session.get("messages", [])
            }
        
        # Create new session
        session_id = str(uuid.uuid4())
        
        # Initialize Gemini chat
        gemini_chat = GeminiChat(settings.GEMINI_API_KEY)
        gemini_chat.set_context(
            transcript=summary.get("transcript", ""),
            summary=summary.get("text_summary", ""),
            video_info=summary.get("video_info", {}),
            key_points=summary.get("key_points", [])
        )
        
        # Store session
        chat_sessions[session_id] = gemini_chat
        
        # Save to database
        session_data = {
            "session_id": session_id,
            "user_id": "test_user",
            "video_id": summary.get("video_id", ""),
            "summary_id": summary_id,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.chat_sessions.insert_one(session_data)
        
        return {
            "session_id": session_id,
            "messages": []
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/session/{session_id}/ask")
async def ask_question(session_id: str, question: str):
    """Ask a question in a chat session (no auth for testing)"""
    try:
        db = await get_database()
        
        # Get session
        session = await db.chat_sessions.find_one({"session_id": session_id})
        
        if not session:
            raise HTTPException(404, "Chat session not found")
        
        # Get Gemini chat instance
        gemini_chat = chat_sessions.get(session_id)
        
        if not gemini_chat:
            # Recreate if lost
            summary = await db.summaries.find_one({"summary_id": session["summary_id"]})
            
            gemini_chat = GeminiChat(settings.GEMINI_API_KEY)
            gemini_chat.set_context(
                transcript=summary.get("transcript", ""),
                summary=summary.get("text_summary", ""),
                video_info=summary.get("video_info", {}),
                key_points=summary.get("key_points", [])
            )
            chat_sessions[session_id] = gemini_chat
        
        # Get answer
        answer = await gemini_chat.ask_question(question)
        
        # Save messages
        messages = session.get("messages", [])
        messages.append({
            "role": "user",
            "content": question,
            "timestamp": datetime.utcnow().isoformat()
        })
        messages.append({
            "role": "assistant",
            "content": answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await db.chat_sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "messages": messages,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "answer": answer,
            "messages": messages[-10:]  # Return last 10 messages
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))

@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, session_id)
    
    try:
        db = await get_database()
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            question = data.get("question", "")
            
            # Get session
            session = await db.chat_sessions.find_one({"session_id": session_id})
            
            if not session:
                await manager.send_message({
                    "error": "Session not found"
                }, session_id)
                continue
            
            # Get Gemini chat
            gemini_chat = chat_sessions.get(session_id)
            
            if not gemini_chat:
                summary = await db.summaries.find_one({
                    "summary_id": session["summary_id"]
                })
                
                gemini_chat = GeminiChat(settings.GEMINI_API_KEY)
                gemini_chat.set_context(
                    transcript=summary.get("transcript", ""),
                    summary=summary.get("text_summary", ""),
                    video_info=summary.get("video_info", {}),
                    key_points=summary.get("key_points", [])
                )
                chat_sessions[session_id] = gemini_chat
            
            # Get answer
            answer = await gemini_chat.ask_question(question)
            
            # Send response
            await manager.send_message({
                "question": question,
                "answer": answer,
                "timestamp": datetime.utcnow().isoformat()
            }, session_id)
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)