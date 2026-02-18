from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid

from ..models.whisper_model import WhisperTranscriber
from ..models.summarizer import VideoSummarizer
from ..models.video_processor import VideoProcessor

router = APIRouter(prefix="/summarize", tags=["summarize"])

# Initialize models (lazy loading)
transcriber = None
summarizer = None
processor = None

def get_transcriber():
    global transcriber
    if transcriber is None:
        transcriber = WhisperTranscriber("base")
    return transcriber

def get_summarizer():
    global summarizer
    if summarizer is None:
        summarizer = VideoSummarizer()
    return summarizer

def get_processor():
    global processor
    if processor is None:
        processor = VideoProcessor()
    return processor

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
async def summarize_video(request: SummarizeRequest):
    """
    Summarize a video file
    """
    try:
        # Check if video exists
        if not os.path.exists(request.video_path):
            raise HTTPException(404, "Video file not found")
        
        # Generate summary ID
        summary_id = str(uuid.uuid4())
        
        # Get video info
        processor = get_processor()
        video_info = processor.get_video_info(request.video_path)
        
        # Transcribe video
        transcriber = get_transcriber()
        segments = transcriber.get_segments(request.video_path)
        
        # Get full transcript
        transcript = " ".join([seg['text'] for seg in segments])
        
        # Rank segments by importance
        summarizer = get_summarizer()
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
        key_points = summarizer.extract_key_sentences(transcript)
        
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

@router.post("/{summary_id}/video")
async def create_summary_video(summary_id: str, video_path: str, segments: List[dict]):
    """
    Create a summary video from selected segments
    """
    try:
        output_path = f"../processed/summary_{summary_id}.mp4"
        
        processor = get_processor()
        result = processor.create_summary_video(video_path, segments, output_path)
        
        return {
            "success": True,
            "summary_video": output_path,
            "message": "Summary video created"
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))
