"""
summarize.py — async summarization pipeline with background task offloading.

Flow:
  POST /api/summarize/  → enqueues job, returns 202 + task_id
  GET  /api/summarize/status/{task_id} → poll until status == "done" | "failed"
  GET  /api/summarize/history          → list user's completed summaries
  GET  /api/summarize/{summary_id}     → fetch one summary
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from ..core.config import settings
from ..core.database import get_database
from ..core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory task status store
# { task_id: {"status": "pending"|"processing"|"done"|"failed", "summary_id": str, "error": str} }
_task_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SummarizeRequest(BaseModel):
    video_path: str
    summary_ratio: Optional[float] = 0.3
    max_summary_length: Optional[int] = 300


class TaskAccepted(BaseModel):
    task_id: str
    status: str = "pending"
    message: str = "Summarization queued. Poll /api/summarize/status/{task_id} for progress."


# ---------------------------------------------------------------------------
# Background pipeline
# ---------------------------------------------------------------------------

async def _run_summarize_pipeline(
    task_id: str,
    request: SummarizeRequest,
    user_id: str,
    whisper,
    summarizer,
):
    _task_store[task_id]["status"] = "processing"

    try:
        # 1. Transcribe (CPU-heavy — run in thread)
        logger.info("Task %s: starting transcription", task_id)
        segments = await asyncio.to_thread(whisper.get_segments, request.video_path)
        transcript = " ".join(seg.get("text", "") for seg in segments) or "No transcript available."

        # 2. Rank + select segments
        ranked = await asyncio.to_thread(summarizer.rank_segments, segments)
        num_segs = max(1, int(len(ranked) * request.summary_ratio))
        selected = ranked[:num_segs]

        # 3. Summarize (also CPU-heavy)
        logger.info("Task %s: summarizing", task_id)
        text_summary = await asyncio.to_thread(
            summarizer.summarize_text, transcript, request.max_summary_length
        )

        # 4. Key points
        key_points = await asyncio.to_thread(summarizer.extract_key_points, transcript)

        # 5. Persist to DB
        summary_id = str(uuid.uuid4())

        # Resolve the file_id from the DB to enable streaming by ID
        db = await get_database()
        video_record = await db.videos.find_one({"file_path": request.video_path})
        resolved_file_id = video_record["file_id"] if video_record else Path(request.video_path).stem

        video_info = {
            "file_id":  resolved_file_id,
            "path":     request.video_path,
            "filename": Path(request.video_path).name,
            "size":     os.path.getsize(request.video_path),
        }

        await db.summaries.insert_one({
            "summary_id": summary_id,
            "task_id": task_id,
            "video_id": Path(request.video_path).stem,
            "user_id": user_id,
            "transcript": transcript[:5000],          # store up to 5k chars
            "text_summary": text_summary,
            "key_points": key_points,
            "segments": selected,
            "video_info": video_info,
            "language": "auto",
            "created_at": datetime.now(timezone.utc),
        })

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
    # Validate path
    if not os.path.exists(request.video_path):
        raise HTTPException(
            status_code=404,
            detail={"code": "VIDEO_NOT_FOUND", "message": "Video file not found at the given path."},
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

    background_tasks.add_task(
        _run_summarize_pipeline,
        task_id,
        request,
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
        return {"summaries": summaries}
    except Exception as e:
        logger.exception("Failed to fetch summary history: %s", e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": "Failed to retrieve summaries."})


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
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch summary %s: %s", summary_id, e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": "Failed to retrieve summary."})