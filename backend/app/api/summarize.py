"""
summarize.py — async summarization pipeline with background task offloading.

Flow:
  POST /api/summarize/  → enqueues job, returns 202 + task_id
  GET  /api/summarize/status/{task_id} → poll until status == "done" | "failed"
  GET  /api/summarize/history          → list user's completed summaries
  GET  /api/summarize/{summary_id}     → fetch one summary
  GET  /api/summarize/video/{summary_id}/stream → stream the summarized video
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import numpy as np

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..core.config import settings
from ..core.database import get_database
from ..core.security import get_current_user
from fastapi import File, UploadFile
import tempfile
import shutil
from youtube_transcript_api import YouTubeTranscriptApi
from ..models.summarizer import VideoSummarizer

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory task status store
# { task_id: {"status": "pending"|"processing"|"done"|"failed", "summary_id": str, "error": str} }
_task_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SummarizeRequest(BaseModel):
    file_id: str
    summary_ratio: Optional[float] = 0.3
    max_summary_length: Optional[int] = 500  # Increased for more detail

class YouTubeSummarizeRequest(BaseModel):
    url: str


class TaskAccepted(BaseModel):
    task_id: str
    status: str = "pending"
    message: str = "Summarization queued. Poll /api/summarize/status/{task_id} for progress."


# ---------------------------------------------------------------------------
# Background pipeline
# ---------------------------------------------------------------------------

async def _run_summarize_pipeline(
    task_id: str,
    video_path: str,
    summary_ratio: float,
    max_summary_length: int,
    user_id: str,
    whisper,
    summarizer,
):
    _task_store[task_id]["status"] = "processing"

    try:
        # 1. Transcribe (CPU-heavy — run in thread)
        logger.info("Task %s: starting transcription", task_id)
        segments = await asyncio.to_thread(whisper.get_segments, video_path)
        transcript = " ".join(seg.get("text", "") for seg in segments) or "No transcript available."

        # 2. Rank + select segments
        ranked = await asyncio.to_thread(summarizer.rank_segments, segments)
        total_segs = len(ranked)
        num_segs = max(1, int(total_segs * summary_ratio))
        
        # Pick segments evenly spread across the timeline
        if total_segs > num_segs:
            indices = np.linspace(0, total_segs - 1, num_segs, dtype=int)
            selected = [ranked[i] for i in indices]
        else:
            selected = ranked

        # 3. Summarize (also CPU-heavy)
        logger.info("Task %s: summarizing", task_id)
        text_summary = await asyncio.to_thread(
            summarizer.summarize_text, transcript, max_summary_length
        )

        # 4. Key points
        key_points = await asyncio.to_thread(summarizer.extract_key_points, transcript)

        # 5. Generate visual summary video (slideshow with key frames + text)
        summary_video_path = None
        try:
            from ..models.video_processor import VideoProcessor
            processor = VideoProcessor()

            # Build per-user processed dir
            processed_dir = Path(settings.PROCESSED_DIR) / user_id
            processed_dir.mkdir(parents=True, exist_ok=True)

            summary_video_filename = f"summary_{task_id}.mp4"
            summary_video_output = str(processed_dir / summary_video_filename)

            # Derive a friendly title from the original filename
            video_title = Path(video_path).stem.replace("_", " ").replace("-", " ").title()

            logger.info("Task %s: generating enhanced visual summary video", task_id)
            await asyncio.to_thread(
                processor.create_visual_summary,
                video_path,
                text_summary,
                key_points,
                summary_video_output,
                video_title,
                0,        # auto key frames
                selected  # Use the ranked segments
            )
            if os.path.exists(summary_video_output):
                summary_video_path = summary_video_output
                logger.info("Task %s: visual summary video created at %s", task_id, summary_video_path)
            else:
                logger.warning("Task %s: summary video file not found after creation", task_id)
        except Exception as vid_err:
            # Don't fail the whole pipeline if video creation fails
            logger.warning("Task %s: summary video generation failed (non-fatal): %s", task_id, vid_err)

        # 6. Persist to DB
        summary_id = str(uuid.uuid4())

        # Resolve the file_id from the DB to enable streaming by ID
        db = await get_database()
        video_record = await db.videos.find_one({"file_path": video_path})
        resolved_file_id = video_record["file_id"] if video_record else Path(video_path).stem

        video_info = {
            "file_id":  resolved_file_id,
            "path":     video_path,
            "filename": Path(video_path).name,
            "size":     os.path.getsize(video_path),
        }

        summary_doc = {
            "summary_id": summary_id,
            "task_id": task_id,
            "video_id": Path(video_path).stem,
            "user_id": user_id,
            "transcript": transcript[:5000],          # store up to 5k chars
            "text_summary": text_summary,
            "key_points": key_points,
            "segments": selected,
            "video_info": video_info,
            "language": "auto",
            "created_at": datetime.now(timezone.utc),
        }

        # Add summary video info if it was generated
        if summary_video_path:
            summary_doc["summary_video_path"] = summary_video_path
            summary_doc["summary_video_size"] = os.path.getsize(summary_video_path)

        await db.summaries.insert_one(summary_doc)

        _task_store[task_id].update({"status": "done", "summary_id": summary_id})
        logger.info("Task %s: done, summary_id=%s", task_id, summary_id)

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        _task_store[task_id].update({"status": "failed", "error": str(e)})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", response_model=TaskAccepted, status_code=202)
async def summarize_video(
    request: SummarizeRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Queue a summarization job. Returns 202 immediately with a task_id."""
    db = await get_database()
    video_record = await db.videos.find_one({"file_id": request.file_id, "user_id": str(current_user["_id"])})
    
    if not video_record or "file_path" not in video_record:
        raise HTTPException(
            status_code=404,
            detail={"code": "VIDEO_NOT_FOUND", "message": "Video file not found or you do not have permission."},
        )

    # Validate path exists on disk
    if not os.path.exists(video_record["file_path"]):
        raise HTTPException(
            status_code=404,
            detail={"code": "FILE_MISSING", "message": "The actual video file is missing from the server storage."},
        )

    # Get singleton models from app state
    whisper = getattr(http_request.app.state, "whisper", None)
    summarizer = getattr(http_request.app.state, "summarizer", None)

    if whisper is None or summarizer is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "MODELS_UNAVAILABLE", "message": "ML models are not loaded. Contact the administrator."},
        )

    task_id = str(uuid.uuid4())
    _task_store[task_id] = {"status": "pending", "summary_id": None, "error": None}

    # Pass the actual absolute string path to the pipeline thread
    background_tasks.add_task(
        _run_summarize_pipeline,
        task_id,
        video_record["file_path"],
        request.summary_ratio,
        request.max_summary_length,
        str(current_user["_id"]),
        whisper,
        summarizer,
    )

    return TaskAccepted(task_id=task_id)


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),  # noqa: keep auth
):
    """Poll for summarization job status."""
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TASK_NOT_FOUND", "message": "Task ID not found. It may have expired."},
        )
    return {"task_id": task_id, **task}


@router.get("/history")
async def get_summary_history(current_user: dict = Depends(get_current_user)):
    """Return all summaries created by the current user."""
    try:
        db = await get_database()
        cursor = db.summaries.find({"user_id": str(current_user["_id"])}).sort("created_at", -1)
        summaries = await cursor.to_list(length=50)
        for s in summaries:
            s["_id"] = str(s["_id"])
            s["has_summary_video"] = bool(s.get("summary_video_path")) and os.path.exists(
                s.get("summary_video_path", "")
            )
        return {"summaries": summaries}
    except Exception as e:
        logger.exception("Failed to fetch summary history: %s", e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": "Failed to retrieve summaries."})

@router.get("/video/{summary_id}/stream")
async def stream_summary_video(
    summary_id: str,
    token: str = "",
):
    """
    Stream the generated summary video to the browser.
    Accepts the JWT as ?token= query param because browser <video> elements
    cannot send custom Authorization headers.
    """
    from ..core.security import get_current_user_from_token
    user = await get_current_user_from_token(token)
    if user is None:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Invalid or missing token."})

    try:
        db = await get_database()
        summary = await db.summaries.find_one({
            "summary_id": summary_id,
            "user_id": str(user["_id"]),
        })
        if not summary:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Summary not found."})

        video_path = summary.get("summary_video_path")
        if not video_path or not os.path.exists(video_path):
            raise HTTPException(
                404,
                detail={"code": "VIDEO_NOT_FOUND", "message": "Summary video not available for this summary."},
            )

        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=f"summary-{summary_id[:8]}.mp4",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to stream summary video %s: %s", summary_id, e)
        raise HTTPException(500, detail={"code": "STREAM_FAILED", "message": "Failed to stream summary video."})


@router.get("/video/direct/{filename}")
async def get_direct_video(filename: str, current_user: dict = Depends(get_current_user)):
    """Stream a video directly by filename for quick summaries."""
    # Build per-user processed dir path
    user_id = str(current_user["_id"])
    file_path = Path(settings.PROCESSED_DIR) / user_id / filename
    
    if not file_path.exists():
        raise HTTPException(404, detail="Video not found")
        
    return FileResponse(file_path, media_type="video/mp4")


@router.get("/{summary_id}")
async def get_summary(
    summary_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Fetch a specific summary by ID."""
    try:
        db = await get_database()
        summary = await db.summaries.find_one({
            "summary_id": summary_id,
            "user_id": str(current_user["_id"]),
        })
        if not summary:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Summary not found."})
        summary["_id"] = str(summary["_id"])

        # Add a flag indicating whether a summary video is available
        summary["has_summary_video"] = bool(summary.get("summary_video_path")) and os.path.exists(
            summary.get("summary_video_path", "")
        )

        return summary
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.exception("Failed to fetch summary %s: %s", summary_id, e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": f"Failed to retrieve summary. {str(e)}", "trace": err_msg})

@router.get("/debug/tasks")
async def debug_tasks():
    global _task_store
    return _task_store

@router.get("/debug/{summary_id}")
async def debug_summary(summary_id: str):
    db = await get_database()
    summary = await db.summaries.find_one({"summary_id": summary_id})
    if not summary:
        return {"error": "not found"}
    summary["_id"] = str(summary["_id"])
    summary["has_summary_video"] = bool(summary.get("summary_video_path")) and os.path.exists(
            summary.get("summary_video_path", "")
    )
    return summary

def extract_youtube_id(url: str) -> str:
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch':
            q = parse_qs(parsed.query)
            return q['v'][0] if 'v' in q else ""
        if parsed.path.startswith('/embed/'):
            return parsed.path[7:]
        if parsed.path.startswith('/v/'):
            return parsed.path[3:]
    return ""

@router.post("/summarize-youtube")
async def summarize_youtube_sync(
    req: YouTubeSummarizeRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Synchronous YouTube summarization endpoint."""
    try:
        video_id = extract_youtube_id(req.url)
        if not video_id:
            raise HTTPException(400, detail="Could not extract YouTube video ID")

        # Use newer instance-based fetch()
        yt_api = YouTubeTranscriptApi()
        transcript_list = yt_api.fetch(video_id)
        full_text = " ".join([t['text'] for t in transcript_list])
        
        # Reuse pre-loaded summarizer if available
        summarizer = getattr(request.app.state, "summarizer", VideoSummarizer())
        summary = summarizer.summarize_hf(full_text)
        
        return {"summary": summary}
    except Exception as e:
        logger.error(f"YouTube summarization failed: {e}")
        raise HTTPException(500, detail=str(e))

@router.post("/summarize-video")
async def summarize_video_sync(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Synchronous local video summarization endpoint using moviepy."""
    temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        # 1. Save upload
        shutil.copyfileobj(file.file, temp_video)
        temp_video.close()
        temp_audio.close()

        # 2. Extract audio via moviepy
        try:
            from moviepy import VideoFileClip
        except ImportError:
            from moviepy.editor import VideoFileClip
            
        clip = VideoFileClip(temp_video.name)
        clip.audio.write_audiofile(temp_audio.name, fps=16000, nbytes=2, codec='pcm_s16le')
        clip.close()

        # 3. Transcribe - reuse pre-loaded whisper if available
        whisper_model = getattr(request.app.state, "whisper", None)
        if whisper_model:
            # Use the existing whisper class get_segments or similar?
            # Actually whisper_model is a WhisperTranscriber instance
            # Let's just use the raw model if we can, or load a small one.
            # whisper_model.get_segments(temp_video.name) is what we usually do.
            # But here we already have the audio.
            import whisper
            # If whisper_model has a .model attribute (standard in this app)
            model = getattr(whisper_model, "model", whisper.load_model("base"))
            result = model.transcribe(temp_audio.name)
        else:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(temp_audio.name)
            
        transcript = result["text"]

        # 4. Summarize - reuse pre-loaded summarizer
        summarizer = getattr(request.app.state, "summarizer", VideoSummarizer())
        summary = summarizer.summarize_hf(transcript)

        # 5. Generate Highlight Video (Sync)
        summary_video_path = None
        try:
            from ..models.video_processor import VideoProcessor
            processor = VideoProcessor()
            user_id = str(current_user["_id"])
            processed_dir = Path(settings.PROCESSED_DIR) / user_id
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            output_filename = f"quick_summary_{uuid.uuid4().hex[:8]}.mp4"
            output_path = str(processed_dir / output_filename)
            
            # For a clear summary, pick more segments
            all_segments = result.get("segments", [])
            num_to_pick = min(12, len(all_segments))
            if len(all_segments) > num_to_pick:
                indices = np.linspace(0, len(all_segments) - 1, num_to_pick, dtype=int)
                selected_segs = [all_segments[i] for i in indices]
            else:
                selected_segs = all_segments
            
            # Extract key points to make the summary clearer
            key_points = summarizer.extract_key_points(transcript)
            
            processor.create_visual_summary(
                temp_video.name, 
                summary,
                key_points,
                output_path, 
                video_title=file.filename,
                segments=selected_segs
            )
            if os.path.exists(output_path):
                summary_video_path = f"/api/summarize/video/direct/{output_filename}"
        except Exception as ve:
            logger.warning("Sync video highlight failed: %s", ve)

        return {
            "summary": summary,
            "video_url": summary_video_path
        }
    except Exception as e:
        logger.error(f"Local video summarization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_video.name): 
            try:
                os.unlink(temp_video.name)
            except Exception:
                pass
        if os.path.exists(temp_audio.name): 
            try:
                os.unlink(temp_audio.name)
            except Exception:
                pass