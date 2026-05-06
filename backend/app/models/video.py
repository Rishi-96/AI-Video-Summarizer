"""
video.py — Pydantic schemas for Video, Summary, and ChatSession documents.

These are used for request/response validation ONLY.
Actual DB operations use raw Motor queries (no ORM).
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# ─── Video ────────────────────────────────────────────────────────────────────

class VideoCreate(BaseModel):
    """Fields written to MongoDB when a video is uploaded."""
    file_id: str
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
    status: str = "uploaded"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VideoResponse(BaseModel):
    """Subset of fields returned to the frontend."""
    file_id: str
    filename: str
    original_name: str
    file_size: int
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Summary ─────────────────────────────────────────────────────────────────

class SummaryCreate(BaseModel):
    """Fields written to MongoDB when a summary is created."""
    summary_id: str
    task_id: str
    video_id: str
    user_id: str
    transcript: str
    text_summary: str
    key_points: List[str]
    segments: List[Dict]
    video_info: Dict
    language: str = "auto"
    summary_video_path: Optional[str] = None
    summary_video_size: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryResponse(BaseModel):
    """Subset of fields returned to the frontend."""
    summary_id: str
    video_id: str
    text_summary: str
    key_points: List[str]
    has_summary_video: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Chat Session ────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    """Fields written to MongoDB when a chat session starts."""
    session_id: str
    user_id: str
    video_id: str
    summary_id: str
    messages: List[Dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)