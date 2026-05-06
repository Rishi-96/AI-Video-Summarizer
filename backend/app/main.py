import logging
import uuid
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .api import auth, videos, chat
from .core.config import settings
from .core.database import database

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    filename='app_debug.log',
    filemode='a',
    encoding='utf-8',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# ─── SSL Fix ──────────────────────────────────────────────────────────────────
# Instead of globally disabling SSL verification (MITM vulnerability),
# we only suppress urllib3 warnings and set proxy-specific env vars.
# If you're behind a corporate proxy (Zscaler), set SSL_CERT_FILE or
# REQUESTS_CA_BUNDLE in your .env to point to the proxy's CA bundle.
#
# Example:  SSL_CERT_FILE=C:/path/to/zscaler-ca-bundle.pem
#
# For development ONLY, the DISABLE_SSL_VERIFY=true flag below allows
# insecure connections.  NEVER use this in production.

_disable_ssl = os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true"

if _disable_ssl:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ["CURL_CA_BUNDLE"] = ""
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
    logging.getLogger(__name__).warning(
        "⚠️  SSL verification DISABLED (DISABLE_SSL_VERIFY=true). "
        "Do NOT use this in production."
    )

logger = logging.getLogger(__name__)
logger.info("Main module loading...")

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Optional heavy ML modules ───────────────────────────────────────────────
_summarize_available = False
try:
    from .api import summarize as summarize_router
    _summarize_available = True
except ImportError as e:
    logger.warning("Summarize module not available (missing ML packages): %s", e)

# ─── ML singleton state ──────────────────────────────────────────────────────
_whisper_instance = None
_summarizer_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    # ── startup ──
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

    # ── shutdown ──
    await database.close()


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Video Summarizer API",
    version="2.1.0",
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[url.strip() for url in settings.FRONTEND_URL.split(",") if url.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global exception handler ────────────────────────────────────────────────
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

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router,   prefix="/api/auth",     tags=["auth"])
app.include_router(videos.router, prefix="/api/videos",   tags=["videos"])
app.include_router(chat.router,   prefix="/api/chat",     tags=["chat"])
if _summarize_available:
    app.include_router(summarize_router.router, prefix="/api/summarize", tags=["summarize"])

# ─── Utility endpoints ───────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message": "AI Video Summarizer API",
        "version": "2.1.0",
        "status": "running",
    }


@app.get("/api/health")
async def health_check():
    """Production health check — used by Docker HEALTHCHECK and monitoring."""
    import time

    # Check DB connectivity
    db_status = "unknown"
    try:
        db = database.get_db()
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:80]}"

    # Check storage
    from .core.storage import get_storage
    storage = get_storage()
    storage_type = type(storage).__name__

    models_status = {
        "whisper": "loaded" if getattr(app.state, "whisper", None) else "on-demand",
        "summarizer": "loaded" if getattr(app.state, "summarizer", None) else "on-demand",
    }

    route_count = len([r for r in app.routes if hasattr(r, "path")])

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "storage": storage_type,
        "models": models_status,
        "routes": route_count,
        "upload_dir": settings.UPLOAD_DIR,
    }
