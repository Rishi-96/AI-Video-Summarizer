from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "video_summarizer")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # File Upload
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "524288000"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    PROCESSED_DIR: str = os.getenv("PROCESSED_DIR", "processed")
    
    # Model Settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "tiny")
    SUMMARY_RATIO: float = float(os.getenv("SUMMARY_RATIO", "0.3"))
    
    # Frontend
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    class Config:
        case_sensitive = True

settings = Settings()