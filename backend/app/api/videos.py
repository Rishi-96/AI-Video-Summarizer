import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import aiofiles
import yt_dlp
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..core.config import settings
from ..core.database import get_database
from ..core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
}

# Map extensions to proper MIME types for streaming
EXT_MIME = {
    ".mp4":  "video/mp4",
    ".mov":  "video/quicktime",
    ".avi":  "video/x-msvideo",
    ".mkv":  "video/x-matroska",
    ".webm": "video/webm",
}

MAX_UPLOAD_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024



class YouTubeRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_upload_dir(user_id: str) -> Path:
    """Return (and create) per-user upload subdirectory."""
    d = Path(settings.UPLOAD_DIR) / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _validate_youtube_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.hostname not in ("www.youtube.com", "youtube.com", "youtu.be"):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_YOUTUBE_URL", "message": "Invalid YouTube URL. Must be a youtube.com or youtu.be link."},
        )


async def _save_upload(file: UploadFile, dest: Path) -> None:
    """Async write uploaded file to dest using aiofiles."""
    async with aiofiles.open(dest, "wb") as out:
        while True:
            chunk = await file.read(1024 * 256)  # 256 KB chunks
            if not chunk:
                break
            await out.write(chunk)


async def _yt_download(url: str, output_template: str) -> dict:
    """Run yt_dlp download in a thread to avoid blocking the event loop."""
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_template,
        "quiet": True,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return {
                "filepath": ydl.prepare_filename(info),
                "title": info.get("title", "YouTube Video"),
            }

    return await asyncio.to_thread(_download)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a local video file."""
    # 1. Content-type validation
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"File type '{file.content_type}' is not allowed. Supported types: {sorted(ALLOWED_CONTENT_TYPES)}",
            },
        )

    user_id = str(current_user["_id"])
    upload_dir = _user_upload_dir(user_id)

    file_id = str(uuid.uuid4())
    extension = Path(file.filename or "video.mp4").suffix or ".mp4"
    filename = f"{file_id}{extension}"
    filepath = upload_dir / filename

    try:
        # 2. Stream-write via aiofiles (non-blocking)
        bytes_written = 0
        async with aiofiles.open(filepath, "wb") as out:
            while True:
                chunk = await file.read(1024 * 256)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    await out.close()
                    filepath.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "code": "FILE_TOO_LARGE",
                            "message": f"File exceeds the {settings.MAX_FILE_SIZE_MB} MB limit.",
                        },
                    )
                await out.write(chunk)

        file_size = filepath.stat().st_size

        # 3. Persist to database
        db = await get_database()
        video_data = {
            "file_id": file_id,
            "user_id": user_id,
            "filename": filename,
            "original_name": file.filename,
            "file_path": str(filepath),
            "file_size": file_size,
            "status": "uploaded",
            "created_at": datetime.now(timezone.utc),
        }
        await db.videos.insert_one(video_data)

        logger.info("Video uploaded: file_id=%s user=%s size_mb=%.2f", file_id, user_id, file_size / 1_048_576)

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "original_name": file.filename,
            "size_mb": round(file_size / 1_048_576, 2),
            "message": "File uploaded successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed for user %s: %s", user_id, e)
        filepath.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "UPLOAD_FAILED", "message": "Video upload failed. Please try again."},
        )


@router.post("/upload/youtube")
async def upload_youtube(
    request: YouTubeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Download and process a YouTube video (runs in a thread pool)."""
    _validate_youtube_url(request.url)

    user_id = str(current_user["_id"])
    upload_dir = _user_upload_dir(user_id)
    file_id = str(uuid.uuid4())
    output_template = str(upload_dir / f"{file_id}.%(ext)s")

    try:
        result = await _yt_download(request.url, output_template)
        filepath = Path(result["filepath"])
        original_title = result["title"]
        filename = filepath.name
        file_size = filepath.stat().st_size

        db = await get_database()
        video_data = {
            "file_id": file_id,
            "user_id": user_id,
            "filename": filename,
            "original_name": f"{original_title}.mp4",
            "file_path": str(filepath),
            "file_size": file_size,
            "status": "uploaded",
            "created_at": datetime.now(timezone.utc),
        }
        await db.videos.insert_one(video_data)

        logger.info("YouTube video downloaded: file_id=%s user=%s", file_id, user_id)

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "original_name": f"{original_title}.mp4",
            "size_mb": round(file_size / 1_048_576, 2),
            "message": "YouTube video processed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("YouTube download failed for user %s url=%s: %s", user_id, request.url, e)
        raise HTTPException(
            status_code=500,
            detail={"code": "YOUTUBE_DOWNLOAD_FAILED", "message": f"Error processing YouTube video: {str(e)}"},
        )


@router.get("/")
async def get_videos(current_user: dict = Depends(get_current_user)):
    """Get all videos for the current user."""
    try:
        db = await get_database()
        cursor = db.videos.find({"user_id": str(current_user["_id"])}).sort("created_at", -1)
        videos = await cursor.to_list(length=100)
        for v in videos:
            v["_id"] = str(v["_id"])
        return {"videos": videos}
    except Exception as e:
        logger.exception("Failed to list videos: %s", e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": "Failed to retrieve videos."})



@router.get("/stream/{file_id}")
async def stream_video(file_id: str, token: str = ""):
    """
    Stream a video file to the browser.
    Accepts the JWT as ?token= query param because browser <video> elements
    cannot send custom Authorization headers.
    """
    # Validate token manually (same logic as get_current_user)
    from ..core.security import get_current_user_from_token
    user = await get_current_user_from_token(token)
    if user is None:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Invalid or missing token."})

    try:
        db = await get_database()
        video = await db.videos.find_one({"file_id": file_id, "user_id": str(user["_id"])})
        if not video:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Video not found."})

        file_path = Path(video["file_path"])
        if not file_path.exists():
            raise HTTPException(404, detail={"code": "FILE_MISSING", "message": "Video file not found on disk."})

        extension = file_path.suffix.lower()
        media_type = EXT_MIME.get(extension, "video/mp4")

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=video.get("filename", file_path.name),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to stream video %s: %s", file_id, e)
        raise HTTPException(500, detail={"code": "STREAM_FAILED", "message": "Failed to stream video."})


@router.get("/{file_id}")
async def get_video(file_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single video by file_id."""
    try:
        db = await get_database()
        video = await db.videos.find_one({"file_id": file_id, "user_id": str(current_user["_id"])})
        if not video:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Video not found."})
        video["_id"] = str(video["_id"])
        return video
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get video %s: %s", file_id, e)
        raise HTTPException(500, detail={"code": "FETCH_FAILED", "message": "Failed to retrieve video."})


@router.delete("/{file_id}")
async def delete_video(file_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a video and its associated summaries."""
    try:
        db = await get_database()
        video = await db.videos.find_one({"file_id": file_id, "user_id": str(current_user["_id"])})
        if not video:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Video not found."})

        # Remove file from disk
        file_path = Path(video["file_path"])
        if file_path.exists():
            await asyncio.to_thread(file_path.unlink)

        await db.videos.delete_one({"file_id": file_id})
        await db.summaries.delete_many({"video_id": file_id})

        logger.info("Video deleted: file_id=%s user=%s", file_id, str(current_user["_id"]))
        return {"success": True, "message": "Video deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete video %s: %s", file_id, e)
        raise HTTPException(500, detail={"code": "DELETE_FAILED", "message": "Failed to delete video."})