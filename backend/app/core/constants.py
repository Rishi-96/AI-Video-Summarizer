"""
constants.py — Single source of truth for all model names, limits, and magic strings.

Change model versions HERE, not scattered across individual files.
"""

# ─── Transcription ────────────────────────────────────────────────────────────
WHISPER_MODEL_NAME = "whisper-large-v3"

# ─── LLM (Summarization & Chat) ──────────────────────────────────────────────
# Groq cloud models — LLaMA 3.3 70B for much better summary quality
GROQ_SUMMARIZATION_MODEL = "llama-3.3-70b-versatile"
GROQ_CHAT_MODEL = "llama-3.3-70b-versatile"

# Ollama local models
OLLAMA_MODEL = "llama3"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

# HuggingFace models
HF_SUMMARIZATION_MODEL = "sshleifer/distilbart-cnn-12-6"

# ─── Video Processing ────────────────────────────────────────────────────────
OUTPUT_VIDEO_WIDTH = 1280
OUTPUT_VIDEO_HEIGHT = 720
OUTPUT_VIDEO_FPS = 24
MAX_CLIPS_PER_SUMMARY = 12
MAX_SEGMENTS_FOR_VIDEO = 10

# ─── Audio ────────────────────────────────────────────────────────────────────
AUDIO_SAMPLE_RATE = 16000      # 16kHz for Whisper
AUDIO_CHANNELS = 1             # Mono
AUDIO_CHUNK_SECONDS = 600      # 10 min chunks for Groq API size limits

# ─── Summarization Defaults ──────────────────────────────────────────────────
DEFAULT_SUMMARY_RATIO = 0.3
DEFAULT_MAX_SUMMARY_LENGTH = 500
MAX_TRANSCRIPT_STORE_CHARS = 5000
MAX_CHAT_TRANSCRIPT_CHARS = 2000
TEXT_CHUNK_MAX_CHARS = 15000   # Safe for 8K token context LLMs

# ─── Task Status ──────────────────────────────────────────────────────────────
TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_TRANSCRIBING = "transcribing"
TASK_STATUS_SUMMARIZING = "summarizing"
TASK_STATUS_GENERATING_VIDEO = "generating_video"
TASK_STATUS_GENERATING_SUBTITLES = "generating_subtitles"
TASK_STATUS_GENERATING_TTS = "generating_tts"
TASK_STATUS_DONE = "done"
TASK_STATUS_FAILED = "failed"

# ─── Rate Limiting ───────────────────────────────────────────────────────────
RATE_LIMIT_AUTH = "5/minute"          # Login/register attempts
RATE_LIMIT_UPLOAD = "10/minute"       # Video uploads
RATE_LIMIT_SUMMARIZE = "5/minute"     # Summarization requests
RATE_LIMIT_CHAT = "30/minute"         # Chat messages
RATE_LIMIT_DEFAULT = "60/minute"      # General API calls

# ─── TTS (Text-to-Speech) ────────────────────────────────────────────────────
DEFAULT_TTS_VOICE = "en-US-AriaNeural"       # Microsoft Edge TTS voice
DEFAULT_TTS_RATE = "+0%"                      # Speech rate adjustment
DEFAULT_TTS_VOLUME = "+0%"                    # Volume adjustment

# ─── Subtitle Generation ─────────────────────────────────────────────────────
SUBTITLE_FORMAT_SRT = "srt"
SUBTITLE_FORMAT_VTT = "vtt"

# ─── Description Generation ──────────────────────────────────────────────────
DESCRIPTION_TYPES = ["oneliner", "short", "detailed", "seo"]
