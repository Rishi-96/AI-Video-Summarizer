from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
from datetime import datetime

from ..core.database import get_database
from ..core.security import get_current_user
from ..models.whisper_faster import FasterWhisperTranscriber
from ..models.summarizer import VideoSummarizer
from ..core.config import settings

router = APIRouter()

# Initialize models
transcriber = FasterWhisperTranscriber(settings.WHISPER_MODEL)
summarizer = VideoSummarizer()

class SummarizeRequest(BaseModel):
    video_path: str
    summary_ratio: Optional[float] = 0.3
    max_summary_length: Optional[int] = 300

class SummarizeResponse(BaseModel):
    success: bool
    summary_id: str
    transcript: str
    text_summary: str
    key_points: List[str]
    segments: List[dict]
    video_info: dict
    language: str

@router.post("/", response_model=SummarizeResponse)
async def summarize_video(
    request: SummarizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Summarize a video file"""
    try:
        # Check if video exists
        if not os.path.exists(request.video_path):
            raise HTTPException(404, "Video file not found")
        
        # Generate summary ID
        summary_id = str(uuid.uuid4())
        
        # Get video info
        video_info = {
            "path": request.video_path,
            "filename": os.path.basename(request.video_path),
            "size": os.path.getsize(request.video_path)
        }
        
        # Transcribe video
        segments = transcriber.get_segments(request.video_path)
        
        # Get full transcript
        transcript = " ".join([seg.get('text', '') for seg in segments])
        
        if not transcript:
            transcript = "No transcript available for this video."
        
        # Rank segments by importance
        ranked_segments = summarizer.rank_segments(segments)
        
        # Select top segments based on ratio
        num_segments = max(1, int(len(ranked_segments) * request.summary_ratio))
        selected_segments = ranked_segments[:num_segments]
        
        # Generate summary
        text_summary = summarizer.summarize_text(
            transcript,
            max_length=request.max_summary_length
        )
        
        # Extract key points
        key_points = summarizer.extract_key_points(transcript)
        
        # Save to database
        db = await get_database()
        summary_data = {
            "summary_id": summary_id,
            "video_id": os.path.basename(request.video_path).split('.')[0],
            "user_id": str(current_user["_id"]),
            "transcript": transcript[:1000] if len(transcript) > 1000 else transcript,
            "text_summary": text_summary,
            "key_points": key_points,
            "segments": selected_segments,
            "video_info": video_info,
            "language": "en",
            "created_at": datetime.utcnow()
        }
        
        await db.summaries.insert_one(summary_data)
        
        return SummarizeResponse(
            success=True,
            summary_id=summary_id,
            transcript=transcript[:500] + "..." if len(transcript) > 500 else transcript,
            text_summary=text_summary,
            key_points=key_points,
            segments=selected_segments,
            video_info=video_info,
            language="en"
        )
        
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/history")
async def get_summary_history(current_user: dict = Depends(get_current_user)):
    """Get summary history for current user"""
    try:
        db = await get_database()
        cursor = db.summaries.find({"user_id": str(current_user["_id"])}).sort("created_at", -1)
        summaries = await cursor.to_list(length=50)
        
        for summary in summaries:
            summary["_id"] = str(summary["_id"])
        
        return {"summaries": summaries}
        
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/{summary_id}")
async def get_summary(
    summary_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get summary by ID"""
    try:
        db = await get_database()
        summary = await db.summaries.find_one({
            "summary_id": summary_id,
            "user_id": str(current_user["_id"])
        })
        
        if not summary:
            raise HTTPException(404, "Summary not found")
        
        summary["_id"] = str(summary["_id"])
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))