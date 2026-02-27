import logging
import uuid
import ssl
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

# Fix for corporate proxies/Zscaler injecting self-signed certificates
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["CURL_CA_BUNDLE"] = ""


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import auth, videos, chat
from .core.config import settings
from .core.database import database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy ML modules — server still starts without them
# ---------------------------------------------------------------------------
_summarize_available = False
try:
    from .api import summarize as summarize_router
    _summarize_available = True
except ImportError as e:
    logger.warning("Summarize module not available (missing ML packages): %s", e)

# ---------------------------------------------------------------------------
# ML singleton state (populated during lifespan startup)
# ---------------------------------------------------------------------------
_whisper_instance = None
_summarizer_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    # ---- startup ----
    # Database
    try:
        await database.connect()
    except Exception as e:
        logger.warning("Server starting without database: %s", e)

    # Ensure upload/processed directories exist
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.PROCESSED_DIR).mkdir(parents=True, exist_ok=True)

    # Pre-load ML models as app-level singletons
    global _whisper_instance, _summarizer_instance
    if _summarize_available:
        try:
            from .models.whisper_model import WhisperTranscriber
            _whisper_instance = WhisperTranscriber(model_size=settings.WHISPER_MODEL)
            app.state.whisper = _whisper_instance
            logger.info("Whisper model loaded at startup")
        except Exception as e:
            logger.warning("Could not pre-load Whisper: %s", e)
            app.state.whisper = None

        try:
            from .models.summarizer import VideoSummarizer
            _summarizer_instance = VideoSummarizer()
            app.state.summarizer = _summarizer_instance
            logger.info("Summarizer model loaded at startup")
        except Exception as e:
            logger.warning("Could not pre-load Summarizer: %s", e)
            app.state.summarizer = None
    else:
        app.state.whisper = None
        app.state.summarizer = None

    yield

    # ---- shutdown ----
    await database.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Video Summarizer API",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — scoped to configured FRONTEND_URL only
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[url.strip() for url in settings.FRONTEND_URL.split(",") if url.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handler — prevent stack trace leakage
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = str(uuid.uuid4())[:8]
    logger.exception("Unhandled exception [%s]: %s", error_id, exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "error_id": error_id,
            }
        },
    )

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router,   prefix="/api/auth",     tags=["auth"])
app.include_router(videos.router, prefix="/api/videos",   tags=["videos"])
app.include_router(chat.router,   prefix="/api/chat",     tags=["chat"])
if _summarize_available:
    app.include_router(summarize_router.router, prefix="/api/summarize", tags=["summarize"])

# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "AI Video Summarizer API",
        "version": "2.0.0",
        "status": "running",
    }


@app.get("/api/health")
async def health_check():
    models_status = {
        "whisper": "loaded" if getattr(app.state, "whisper", None) else "unavailable",
        "summarizer": "loaded" if getattr(app.state, "summarizer", None) else "unavailable",
    }
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "models": models_status,
        "upload_dir": settings.UPLOAD_DIR,
    }
