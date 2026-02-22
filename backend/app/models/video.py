from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from beanie import Document, Indexed

class Video(Document):
    """Video model"""
    file_id: Indexed(str, unique=True)
    user_id: str
    filename: str
    original_name: str
    file_path: str
    file_size: int
    duration: Optional[float] = 0
    width: Optional[int] = 0
    height: Optional[int] = 0
    fps: Optional[float] = 0
    thumbnail_path: Optional[str] = None
    status: str = "uploaded"  # uploaded, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "videos"
        indexes = [
            "file_id",
            "user_id",
            "status"
        ]

class Summary(Document):
    """Summary model"""
    summary_id: Indexed(str, unique=True)
    video_id: str
    user_id: str
    transcript: str
    text_summary: str
    key_points: List[str]
    segments: List[Dict]
    video_info: Dict
    language: str
    summary_video_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "summaries"
        indexes = [
            "summary_id",
            "video_id",
            "user_id"
        ]

class ChatSession(Document):
    """Chat session model"""
    session_id: Indexed(str, unique=True)
    user_id: str
    video_id: str
    summary_id: str
    messages: List[Dict] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "chat_sessions"
        indexes = [
            "session_id",
            "user_id",
            "video_id"
        ]