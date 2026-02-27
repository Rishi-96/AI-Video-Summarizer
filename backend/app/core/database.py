import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB and create required indexes."""
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
            )
            # Ping to confirm connectivity
            await self.client.server_info()
            self.db = self.client[settings.DATABASE_NAME]
            await self._create_indexes()
            logger.info("Connected to MongoDB: %s", settings.DATABASE_NAME)
        except Exception as e:
            logger.error("MongoDB connection failed: %s", e)
            raise

    async def _create_indexes(self):
        """Create required database indexes (idempotent)."""
        await self.db.users.create_index("email",          unique=True)
        await self.db.videos.create_index("file_id",       unique=True)
        await self.db.videos.create_index("user_id")
        await self.db.summaries.create_index("summary_id", unique=True)
        await self.db.summaries.create_index("user_id")
        await self.db.chat_sessions.create_index("session_id", unique=True)
        logger.debug("MongoDB indexes verified")

    async def close(self):
        """Close the MongoDB client connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
database = Database()


async def get_database():
    """FastAPI dependency — raises 503 if database is not connected."""
    if database.db is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": "Database is not connected. Please check the MongoDB connection.",
            },
        )
    return database.db