from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
import os
import logging


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "video_summarizer"

    # Security — no default; must be supplied via .env
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API Keys
    GROQ_API_KEY: str = ""

    # File Upload
    MAX_FILE_SIZE_MB: int = 500                    # checked before write
    UPLOAD_DIR: str = "uploads"
    PROCESSED_DIR: str = "processed"

    # Model Settings
    WHISPER_MODEL: str = "tiny"
    SUMMARY_RATIO: float = 0.3

    # Logging
    LOG_LEVEL: str = "INFO"

    # Frontend — used for strict CORS
    FRONTEND_URL: str = "http://localhost:3000"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    class Config:
        case_sensitive = True
        extra = "ignore"          # silently ignore unknown env vars (e.g. legacy keys)
        # Resolve .env relative to this file so it's found regardless of CWD
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


settings = Settings()

# Apply log level from settings
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)