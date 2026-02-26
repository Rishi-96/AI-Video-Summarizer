from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from typing import List
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path

from ..core.database import get_database
from ..core.security import get_current_user
from ..models.video import Video
from ..models.video_processor import VideoProcessor
from ..core.config import settings

router = APIRouter()
processor = VideoProcessor()

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file (no auth for testing)"""
    try:
        # Validate file type
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(400, f"File type not allowed. Allowed: {allowed_extensions}")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_extension}"
        
        # Create upload directory
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        filepath = upload_dir / filename
        
        # Save file
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Save to database
        db = await get_database()
        video_data = {
            "file_id": file_id,
            "user_id": "test_user",
            "filename": filename,
            "original_name": file.filename,
            "file_path": str(filepath),
            "file_size": file_size,
            "status": "uploaded",
            "created_at": datetime.utcnow()
        }
        
        await db.videos.insert_one(video_data)
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "original_name": file.filename,
            "size": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "message": "File uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))

@router.get("/")
async def get_videos():
    """Get all videos (no auth for testing)"""
    try:
        db = await get_database()
        cursor = db.videos.find({}).sort("created_at", -1)
        videos = await cursor.to_list(length=100)
        
        # Convert ObjectId to string
        for video in videos:
            video["_id"] = str(video["_id"])
        
        return {"videos": videos}
        
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/{file_id}")
async def get_video(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get video by file_id"""
    try:
        db = await get_database()
        video = await db.videos.find_one({
            "file_id": file_id,
            "user_id": str(current_user["_id"])
        })
        
        if not video:
            raise HTTPException(404, "Video not found")
        
        video["_id"] = str(video["_id"])
        
        return video
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/{file_id}")
async def delete_video(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete video"""
    try:
        db = await get_database()
        video = await db.videos.find_one({
            "file_id": file_id,
            "user_id": str(current_user["_id"])
        })
        
        if not video:
            raise HTTPException(404, "Video not found")
        
        # Delete file
        if os.path.exists(video["file_path"]):
            os.remove(video["file_path"])
        
        # Delete from database
        await db.videos.delete_one({"file_id": file_id})
        
        # Delete associated summaries
        await db.summaries.delete_many({"video_id": file_id})
        
        return {"success": True, "message": "Video deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))