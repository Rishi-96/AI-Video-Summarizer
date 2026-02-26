from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from .config import settings


class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB Atlas"""
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000
            )

            # Test connection
            await self.client.server_info()

            self.db = self.client[settings.DATABASE_NAME]

            # Create indexes
            await self._create_indexes()

            print(f"[OK] Connected to MongoDB: {settings.DATABASE_NAME}")

        except Exception as e:
            print(f"[ERROR] MongoDB connection failed: {e}")
            raise e

    async def _create_indexes(self):
        """Create required database indexes"""
        await self.db.users.create_index("email", unique=True)
        await self.db.videos.create_index("file_id", unique=True)
        await self.db.videos.create_index("user_id")
        await self.db.summaries.create_index("summary_id", unique=True)
        await self.db.summaries.create_index("user_id")
        await self.db.chat_sessions.create_index("session_id", unique=True)

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("[INFO] MongoDB connection closed")


# Create single database instance
database = Database()


# Dependency for routes
async def get_database():
    if database.db is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database not connected. Please check MongoDB connection."
        )
    return database.db