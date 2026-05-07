"""
summarize.py — async summarization pipeline with persistent task store.

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
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.config import settings
from ..core.database import get_database
from ..core.security import get_current_user
from ..core.task_store import create_task, get_task, update_task, mark_done, mark_failed
from ..core.constants import (
    TASK_STATUS_PROCESSING,
    TASK_STATUS_TRANSCRIBING,
    TASK_STATUS_SUMMARIZING,
    TASK_STATUS_GENERATING_VIDEO,
    DEFAULT_SUMMARY_RATIO,
    DEFAULT_MAX_SUMMARY_LENGTH,
    MAX_TRANSCRIPT_STORE_CHARS,
    MAX_SEGMENTS_FOR_VIDEO,
    RATE_LIMIT_SUMMARIZE,
    RATE_LIMIT_DEFAULT,
)
from fastapi import File, UploadFile
import tempfile
import shutil
from youtube_transcript_api import YouTubeTranscriptApi
from ..models.summarizer import VideoSummarizer

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SummarizeRequest(BaseModel):
    file_id: str
    summary_ratio: Optional[float] = DEFAULT_SUMMARY_RATIO
    max_summary_length: Optional[int] = DEFAULT_MAX_SUMMARY_LENGTH


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
    await update_task(task_id, status=TASK_STATUS_PROCESSING, progress=5, step="starting")

    try:
        # ── Step 1: Transcribe (CPU-heavy — run in thread) ────────────
        logger.info("Task %s: starting transcription", task_id)
        await update_task(task_id, status=TASK_STATUS_TRANSCRIBING, progress=10, step="transcribing audio")
        segments = await asyncio.to_thread(whisper.get_segments, video_path)
        transcript = " ".join(seg.get("text", "") for seg in segments) or "No transcript available."
        await update_task(task_id, progress=35, step="transcription complete")

        # ── Step 2: PARALLEL — rank + summarize + key points ──────────
        # These three operations are independent and can run simultaneously
        logger.info("Task %s: parallel processing (rank + summarize + key points)", task_id)
        await update_task(task_id, status=TASK_STATUS_SUMMARIZING, progress=40, step="analyzing content (parallel)")

        rank_task = asyncio.to_thread(summarizer.rank_segments, segments)
        summary_task = asyncio.to_thread(summarizer.summarize_text, transcript, max_summary_length)
        keypoints_task = asyncio.to_thread(summarizer.extract_key_points, transcript)

        ranked, text_summary, key_points = await asyncio.gather(
            rank_task, summary_task, keypoints_task
        )

        await update_task(task_id, progress=65, step="analysis complete")

        # Pass ALL ranked segments to the VideoProcessor — it will internally
        # select clips totalling 55-60% of the original video duration.
        # ranked is sorted by relevance_score descending.
        # segments (all whisper segments) is the full unranked list.

        # ── Step 3: Generate subtitles (fast, parallel with video) ────
        subtitle_paths = {}
        try:
            from ..models.subtitles import generate_subtitles
            processed_dir = Path(settings.PROCESSED_DIR) / user_id
            processed_dir.mkdir(parents=True, exist_ok=True)
            subtitle_paths = await asyncio.to_thread(
                generate_subtitles, segments, str(processed_dir), f"subtitles_{task_id}"
            )
            logger.info("Task %s: subtitles generated", task_id)
        except Exception as sub_err:
            logger.warning("Task %s: subtitle generation failed (non-fatal): %s", task_id, sub_err)

        # ── Step 4: Generate summary video (55-60% of original duration) ────
        summary_video_path = None
        try:
            from ..models.video_processor import VideoProcessor
            processor = VideoProcessor()

            processed_dir = Path(settings.PROCESSED_DIR) / user_id
            processed_dir.mkdir(parents=True, exist_ok=True)

            summary_video_filename = f"summary_{task_id}.mp4"
            summary_video_output = str(processed_dir / summary_video_filename)

            video_title = Path(video_path).stem.replace("_", " ").replace("-", " ").title()

            logger.info("Task %s: generating summary video (~55-60%% of original)", task_id)
            await update_task(task_id, status=TASK_STATUS_GENERATING_VIDEO, progress=70, step="generating summary video (55-60%)")

            # Pass ranked segments (importance-ordered) AND all segments (fallback pool)
            await asyncio.to_thread(
                processor.create_visual_summary,
                video_path,
                text_summary,
                key_points,
                summary_video_output,
                video_title,
                0,          # num_key_frames (unused now)
                ranked,     # segments — importance-ordered for selection
                segments,   # all_segments — full pool for gap-filling
            )
            if os.path.exists(summary_video_output):
                summary_video_path = summary_video_output
                logger.info("Task %s: summary video created at %s", task_id, summary_video_path)
            else:
                logger.warning("Task %s: summary video file not found after creation", task_id)
        except Exception as vid_err:
            logger.warning("Task %s: summary video generation failed (non-fatal): %s", task_id, vid_err)
            import traceback
            logger.debug(traceback.format_exc())

        await update_task(task_id, progress=90, step="saving to database")

        # ── Step 5: Persist to DB ─────────────────────────────────────
        summary_id = str(uuid.uuid4())

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
            "transcript": transcript[:MAX_TRANSCRIPT_STORE_CHARS],
            "full_transcript": transcript,  # store full transcript for subtitles/TTS
            "text_summary": text_summary,
            "key_points": key_points,
            "segments": sorted(ranked, key=lambda s: s.get("start", 0)),
            "all_segments": segments,  # store all segments for subtitle export
            "video_info": video_info,
            "subtitle_paths": subtitle_paths,
            "language": "auto",
            "created_at": datetime.now(timezone.utc),
        }


        # Add summary video info if it was generated
        if summary_video_path:
            summary_doc["summary_video_path"] = summary_video_path
            summary_doc["summary_video_size"] = os.path.getsize(summary_video_path)

        await db.summaries.insert_one(summary_doc)

        await mark_done(task_id, summary_id)
        logger.info("Task %s: done, summary_id=%s", task_id, summary_id)

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        await mark_failed(task_id, str(e))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", response_model=TaskAccepted, status_code=202)
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def summarize_video(
    request: Request,
    body: SummarizeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Queue a summarization job. Returns 202 immediately with a task_id."""
    db = await get_database()
    video_record = await db.videos.find_one({"file_id": body.file_id, "user_id": str(current_user["_id"])})

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
    whisper = getattr(request.app.state, "whisper", None)
    summarizer = getattr(request.app.state, "summarizer", None)

    if whisper is None or summarizer is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "MODELS_UNAVAILABLE", "message": "ML models are not loaded. Contact the administrator."},
        )

    task_id = str(uuid.uuid4())
    user_id = str(current_user["_id"])

    # Persist task to MongoDB (survives restarts)
    await create_task(task_id, user_id)

    # Pass the actual absolute string path to the pipeline thread
    background_tasks.add_task(
        _run_summarize_pipeline,
        task_id,
        video_record["file_path"],
        body.summary_ratio,
        body.max_summary_length,
        user_id,
        whisper,
        summarizer,
    )

    return TaskAccepted(task_id=task_id)


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll for summarization job status."""
    task = await get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TASK_NOT_FOUND", "message": "Task ID not found. It may have expired."},
        )
    return {
        "task_id":    task["task_id"],
        "status":     task["status"],
        "summary_id": task.get("summary_id"),
        "error":      task.get("error"),
        "progress":   task.get("progress", 0),
        "step":       task.get("step", ""),
    }


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
    request: Request,
    summary_id: str,
    token: str = "",
):
    """
    Stream the generated summary video to the browser.
    Accepts the JWT as ?token= query param because browser <video> elements
    cannot send custom Authorization headers.
    Supports HTTP Range requests for proper seeking.
    """
    from ..core.security import get_current_user_from_token
    from fastapi.responses import StreamingResponse

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

        file_size = os.path.getsize(video_path)
        range_header = request.headers.get("range")

        if range_header:
            # Parse Range header: "bytes=start-end"
            range_spec = range_header.replace("bytes=", "")
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            end = min(end, file_size - 1)
            content_length = end - start + 1

            def iter_file():
                with open(video_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                        data = f.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            return StreamingResponse(
                iter_file(),
                status_code=206,
                media_type="video/mp4",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                    "Content-Disposition": f'inline; filename="summary-{summary_id[:8]}.mp4"',
                },
            )

        # No Range header — return full file
        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=f"summary-{summary_id[:8]}.mp4",
            headers={"Accept-Ranges": "bytes"},
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
        logger.exception("Failed to fetch summary %s: %s", summary_id, e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": f"Failed to retrieve summary."})


# ---------------------------------------------------------------------------
# Debug endpoints — SECURED with authentication
# ---------------------------------------------------------------------------

@router.get("/debug/tasks")
async def debug_tasks(current_user: dict = Depends(get_current_user)):
    """List recent tasks for the current user (auth required)."""
    db = await get_database()
    cursor = db.tasks.find({"user_id": str(current_user["_id"])}).sort("created_at", -1).limit(20)
    tasks = await cursor.to_list(length=20)
    for t in tasks:
        t["_id"] = str(t["_id"])
    return {"tasks": tasks}


@router.get("/debug/{summary_id}")
async def debug_summary(summary_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch raw summary document for debugging (auth required, own data only)."""
    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary:
        return {"error": "not found"}
    summary["_id"] = str(summary["_id"])
    summary["has_summary_video"] = bool(summary.get("summary_video_path")) and os.path.exists(
            summary.get("summary_video_path", "")
    )
    return summary


# ---------------------------------------------------------------------------
# YouTube URL parser
# ---------------------------------------------------------------------------

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
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def summarize_youtube_sync(
    request: Request,
    req: YouTubeSummarizeRequest,
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
        summary = await asyncio.to_thread(summarizer.summarize_hf, full_text)

        return {"summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("YouTube summarization failed: %s", e)
        raise HTTPException(500, detail=str(e))


@router.post("/summarize-video")
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def summarize_video_sync(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Synchronous local video summarization endpoint."""
    # ── Content-Length pre-check ──
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds the {settings.MAX_FILE_SIZE_MB} MB limit.",
            },
        )

    temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        # 1. Save upload
        shutil.copyfileobj(file.file, temp_video)
        temp_video.close()
        temp_audio.close()

        # 2. Extract audio via fast ffmpeg (with moviepy fallback)
        from ..core.audio import extract_audio_fast
        audio_path = await asyncio.to_thread(extract_audio_fast, temp_video.name, temp_audio.name)

        # 3. Transcribe - reuse pre-loaded whisper if available
        whisper_model = getattr(request.app.state, "whisper", None)
        if whisper_model:
            import whisper
            model = getattr(whisper_model, "model", whisper.load_model("base"))
            result = await asyncio.to_thread(model.transcribe, audio_path)
        else:
            import whisper
            model = whisper.load_model("base")
            result = await asyncio.to_thread(model.transcribe, audio_path)

        transcript = result["text"]

        # 4. Summarize - reuse pre-loaded summarizer
        summarizer = getattr(request.app.state, "summarizer", VideoSummarizer())
        summary = await asyncio.to_thread(summarizer.summarize_hf, transcript)

        # 5. Generate Highlight Video
        summary_video_path = None
        try:
            from ..models.video_processor import VideoProcessor
            processor = VideoProcessor()
            user_id = str(current_user["_id"])
            processed_dir = Path(settings.PROCESSED_DIR) / user_id
            processed_dir.mkdir(parents=True, exist_ok=True)

            output_filename = f"quick_summary_{uuid.uuid4().hex[:8]}.mp4"
            output_path = str(processed_dir / output_filename)

            all_segments = result.get("segments", [])
            num_to_pick = min(MAX_SEGMENTS_FOR_VIDEO + 2, len(all_segments))
            if len(all_segments) > num_to_pick:
                indices = np.linspace(0, len(all_segments) - 1, num_to_pick, dtype=int)
                selected_segs = [all_segments[i] for i in indices]
            else:
                selected_segs = all_segments

            key_points = await asyncio.to_thread(summarizer.extract_key_points, transcript)

            await asyncio.to_thread(
                processor.create_visual_summary,
                temp_video.name,
                summary,
                key_points,
                output_path,
                video_title=file.filename,
                segments=selected_segs,
            )
            if os.path.exists(output_path):
                summary_video_path = f"/api/summarize/video/direct/{output_filename}"
        except Exception as ve:
            logger.warning("Sync video highlight failed: %s", ve)

        return {
            "summary": summary,
            "video_url": summary_video_path
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Local video summarization failed: %s", e)
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


# ---------------------------------------------------------------------------
# SSE — Real-time progress streaming (replaces polling)
# ---------------------------------------------------------------------------

@router.get("/progress/{task_id}")
async def stream_progress(task_id: str):
    """
    Server-Sent Events endpoint for real-time task progress.

    The frontend can use EventSource to receive live updates instead of
    polling /status/{task_id} every 5 seconds.

    Usage (JS):
        const es = new EventSource('/api/summarize/progress/' + taskId);
        es.onmessage = (e) => { const data = JSON.parse(e.data); ... };
    """
    from fastapi.responses import StreamingResponse
    import json as json_mod

    async def event_generator():
        while True:
            task = await get_task(task_id)
            if task is None:
                yield f"data: {json_mod.dumps({'error': 'Task not found'})}\n\n"
                break

            payload = {
                "task_id":    task["task_id"],
                "status":     task["status"],
                "progress":   task.get("progress", 0),
                "step":       task.get("step", ""),
                "summary_id": task.get("summary_id"),
                "error":      task.get("error"),
            }
            yield f"data: {json_mod.dumps(payload)}\n\n"

            if task["status"] in ("done", "failed"):
                break

            await asyncio.sleep(1)  # 1-second updates (vs 5s polling)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ---------------------------------------------------------------------------
# Subtitle download
# ---------------------------------------------------------------------------

@router.get("/subtitles/{summary_id}/{format}")
async def download_subtitles(
    summary_id: str,
    format: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Download subtitles for a summary in SRT or VTT format.

    If subtitles weren't generated during summarization, they'll be
    generated on-the-fly from the stored segments.
    """
    if format not in ("srt", "vtt"):
        raise HTTPException(400, detail="Format must be 'srt' or 'vtt'")

    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary:
        raise HTTPException(404, detail="Summary not found")

    # Check if pre-generated subtitle file exists
    subtitle_paths = summary.get("subtitle_paths", {})
    if format in subtitle_paths and os.path.exists(subtitle_paths[format]):
        media = "application/x-subrip" if format == "srt" else "text/vtt"
        return FileResponse(
            subtitle_paths[format],
            media_type=media,
            filename=f"subtitles-{summary_id[:8]}.{format}",
        )

    # Generate on-the-fly from stored segments
    segments = summary.get("all_segments") or summary.get("segments", [])
    if not segments:
        raise HTTPException(404, detail="No segments available for subtitle generation")

    from ..models.subtitles import generate_srt, generate_vtt

    processed_dir = Path(settings.PROCESSED_DIR) / str(current_user["_id"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(processed_dir / f"subtitles_{summary_id[:8]}.{format}")

    if format == "srt":
        generate_srt(segments, output_path)
        media = "application/x-subrip"
    else:
        generate_vtt(segments, output_path)
        media = "text/vtt"

    return FileResponse(
        output_path,
        media_type=media,
        filename=f"subtitles-{summary_id[:8]}.{format}",
    )


# ---------------------------------------------------------------------------
# Text-to-Speech
# ---------------------------------------------------------------------------

class TTSRequest(BaseModel):
    summary_id: str
    voice: Optional[str] = "en-US-AriaNeural"
    rate: Optional[str] = "+0%"
    source: Optional[str] = "summary"  # "summary" or "transcript"


@router.post("/tts/generate")
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def generate_tts_audio(
    request: Request,
    body: TTSRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate speech audio from a summary or transcript using edge-tts.

    Returns a URL to download the generated MP3 file.
    """
    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": body.summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary:
        raise HTTPException(404, detail="Summary not found")

    # Select text source
    if body.source == "transcript":
        text = summary.get("full_transcript") or summary.get("transcript", "")
    else:
        text = summary.get("text_summary", "")

    if not text or len(text.strip()) < 10:
        raise HTTPException(400, detail="Not enough text to generate speech")

    # Limit to ~5000 chars to keep file size reasonable
    text = text[:5000]

    processed_dir = Path(settings.PROCESSED_DIR) / str(current_user["_id"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"tts_{body.summary_id[:8]}_{body.source}.mp3"
    output_path = str(processed_dir / output_filename)

    try:
        from ..models.tts import generate_tts
        await generate_tts(text, output_path, body.voice, body.rate)

        return {
            "audio_url": f"/api/summarize/tts/stream/{output_filename}",
            "voice": body.voice,
            "source": body.source,
            "file_size": os.path.getsize(output_path),
        }
    except Exception as e:
        logger.error("TTS generation failed: %s", e)
        raise HTTPException(500, detail=f"TTS generation failed: {str(e)}")


@router.get("/tts/stream/{filename}")
async def stream_tts(filename: str, current_user: dict = Depends(get_current_user)):
    """Stream a generated TTS audio file."""
    user_id = str(current_user["_id"])
    file_path = Path(settings.PROCESSED_DIR) / user_id / filename
    if not file_path.exists():
        raise HTTPException(404, detail="Audio file not found")
    return FileResponse(str(file_path), media_type="audio/mpeg", filename=filename)


@router.get("/tts/voices")
async def list_tts_voices(language: str = "en"):
    """List available TTS voices for a language."""
    try:
        from ..models.tts import list_voices
        voices = await list_voices(language)
        return {"voices": voices, "count": len(voices)}
    except Exception as e:
        logger.error("Failed to list TTS voices: %s", e)
        return {"voices": [], "count": 0, "error": str(e)}


# ---------------------------------------------------------------------------
# Description generation
# ---------------------------------------------------------------------------

class DescriptionRequest(BaseModel):
    summary_id: str
    types: Optional[list] = ["oneliner", "short", "detailed", "seo"]


@router.post("/descriptions/generate")
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def generate_descriptions(
    request: Request,
    body: DescriptionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate multi-level descriptions from a summary.

    Types: oneliner, short, detailed, seo
    """
    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": body.summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary:
        raise HTTPException(404, detail="Summary not found")

    text_summary = summary.get("text_summary", "")
    key_points = summary.get("key_points", [])

    if not text_summary:
        raise HTTPException(400, detail="Summary has no text content")

    # Get summarizer from app state
    summarizer = getattr(request.app.state, "summarizer", None)
    if summarizer is None or summarizer.use_mock:
        raise HTTPException(503, detail="LLM not available for description generation")

    from ..models.descriptions import generate_description
    from ..core.constants import GROQ_SUMMARIZATION_MODEL

    results = {}
    for desc_type in body.types:
        if desc_type not in ["oneliner", "short", "detailed", "seo"]:
            continue
        result = await asyncio.to_thread(
            generate_description,
            text_summary,
            key_points,
            desc_type,
            summarizer.client,
            GROQ_SUMMARIZATION_MODEL,
            summarizer.use_ollama,
            getattr(summarizer, "ollama_url", ""),
        )
        results[desc_type] = result

    return {"summary_id": body.summary_id, "descriptions": results}


# ---------------------------------------------------------------------------
# AI Thumbnail Generation
# ---------------------------------------------------------------------------

@router.post("/thumbnail/{summary_id}")
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def generate_thumbnail_endpoint(
    request: Request,
    summary_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Generate an AI-powered thumbnail for a summarized video."""
    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary:
        raise HTTPException(404, detail="Summary not found")

    video_path = summary.get("video_info", {}).get("path", "")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(404, detail="Original video file not found on server")

    text_summary = summary.get("text_summary", "")
    video_title = Path(video_path).stem.replace("_", " ").replace("-", " ").title()

    processed_dir = Path(settings.PROCESSED_DIR) / str(current_user["_id"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(processed_dir / f"thumb_{summary_id[:8]}.jpg")

    try:
        from ..models.thumbnails import generate_thumbnail
        await asyncio.to_thread(
            generate_thumbnail, video_path, text_summary, output_path, video_title
        )

        # Store thumbnail path in summary
        await db.summaries.update_one(
            {"summary_id": summary_id},
            {"$set": {"thumbnail_path": output_path}},
        )

        return {
            "thumbnail_url": f"/api/summarize/thumbnail/view/{summary_id}",
            "file_size": os.path.getsize(output_path),
        }
    except Exception as e:
        logger.error("Thumbnail generation failed: %s", e)
        raise HTTPException(500, detail=f"Thumbnail generation failed: {str(e)}")


@router.get("/thumbnail/view/{summary_id}")
async def view_thumbnail(
    summary_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Serve a generated thumbnail image."""
    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary or not summary.get("thumbnail_path"):
        raise HTTPException(404, detail="Thumbnail not found")

    thumb_path = summary["thumbnail_path"]
    if not os.path.exists(thumb_path):
        raise HTTPException(404, detail="Thumbnail file missing")

    return FileResponse(thumb_path, media_type="image/jpeg", filename=f"thumbnail-{summary_id[:8]}.jpg")


# ---------------------------------------------------------------------------
# Audio Highlight Detection
# ---------------------------------------------------------------------------

@router.post("/highlights/{summary_id}")
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def detect_highlights_endpoint(
    request: Request,
    summary_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Detect highlight moments in a video using audio energy + speech pace analysis.
    Returns segments sorted by highlight score.
    """
    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary:
        raise HTTPException(404, detail="Summary not found")

    segments = summary.get("all_segments") or summary.get("segments", [])
    if not segments:
        raise HTTPException(400, detail="No segments available for highlight detection")

    # Try to extract audio for energy analysis
    video_path = summary.get("video_info", {}).get("path", "")
    audio_path = None

    if video_path and os.path.exists(video_path):
        try:
            from ..core.audio import extract_audio_fast
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            audio_path = tmp.name
            tmp.close()
            audio_path = await asyncio.to_thread(extract_audio_fast, video_path, audio_path)
        except Exception as e:
            logger.warning("Audio extraction for highlights failed: %s", e)
            audio_path = None

    try:
        from ..models.highlights import detect_highlights
        highlighted = await asyncio.to_thread(detect_highlights, segments, audio_path)

        # Store highlights in summary
        top_highlights = highlighted[:10]
        await db.summaries.update_one(
            {"summary_id": summary_id},
            {"$set": {"highlights": top_highlights}},
        )

        return {
            "summary_id": summary_id,
            "total_segments": len(segments),
            "highlights": top_highlights,
        }
    except Exception as e:
        logger.error("Highlight detection failed: %s", e)
        raise HTTPException(500, detail=f"Highlight detection failed: {str(e)}")
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

class TranslateRequest(BaseModel):
    summary_id: str
    target_lang: str  # ISO 639-1 code: "es", "fr", "ja", etc.


@router.post("/translate")
@limiter.limit(RATE_LIMIT_SUMMARIZE)
async def translate_summary(
    request: Request,
    body: TranslateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Translate a summary and its key points to another language.
    Supports 30+ languages via Groq LLM or NLLB-200 local model.
    """
    db = await get_database()
    summary = await db.summaries.find_one({
        "summary_id": body.summary_id,
        "user_id": str(current_user["_id"]),
    })
    if not summary:
        raise HTTPException(404, detail="Summary not found")

    text_summary = summary.get("text_summary", "")
    key_points = summary.get("key_points", [])

    if not text_summary:
        raise HTTPException(400, detail="No summary text to translate")

    try:
        from ..models.translator import Translator
        translator = Translator()
        result = await asyncio.to_thread(
            translator.translate_summary, text_summary, key_points, body.target_lang
        )

        # Store translation in DB
        translations = summary.get("translations", {})
        translations[body.target_lang] = {
            "summary": result["summary"]["translated"],
            "key_points": result["key_points"],
        }
        await db.summaries.update_one(
            {"summary_id": body.summary_id},
            {"$set": {"translations": translations}},
        )

        return {
            "summary_id": body.summary_id,
            "target_lang": body.target_lang,
            "translated_summary": result["summary"]["translated"],
            "translated_key_points": result["key_points"],
            "backend_used": result["summary"].get("backend_used", "unknown"),
        }
    except Exception as e:
        logger.error("Translation failed: %s", e)
        raise HTTPException(500, detail=f"Translation failed: {str(e)}")


@router.get("/languages")
async def list_languages():
    """List all supported translation languages."""
    from ..models.translator import Translator
    return {"languages": Translator.get_supported_languages()}