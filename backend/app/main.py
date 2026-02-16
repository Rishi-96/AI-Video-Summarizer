from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path

app = FastAPI(title="AI Video Summarizer API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("../uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "AI Video Summarizer API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "backend": "online",
            "database": "checking",
            "ml_models": "loading"
        }
    }

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        # Validate file type
        allowed_types = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska']
        if file.content_type not in allowed_types:
            raise HTTPException(400, f"File type not allowed. Allowed types: {allowed_types}")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{file_id}{file_extension}"
        filepath = UPLOAD_DIR / filename
        
        # Save file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "original_name": file.filename,
            "size": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/files")
async def list_files():
    """List all uploaded files"""
    files = []
    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file():
            stats = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size": stats.st_size,
                "size_mb": round(stats.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stats.st_ctime).isoformat()
            })
    return {"files": files}

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """Delete an uploaded file"""
    filepath = UPLOAD_DIR / filename
    if filepath.exists():
        filepath.unlink()
        return {"success": True, "message": f"File {filename} deleted"}
    raise HTTPException(404, "File not found")
