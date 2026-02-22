from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.DATABASE_NAME]
            
            # Create indexes
            await self.db.users.create_index("email", unique=True)
            await self.db.videos.create_index("file_id", unique=True)
            await self.db.videos.create_index("user_id")
            await self.db.summaries.create_index("summary_id", unique=True)
            await self.db.summaries.create_index("user_id")
            await self.db.chat_sessions.create_index("session_id", unique=True)
            
            print(f"Connected to MongoDB: {settings.DATABASE_NAME}")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")

db = Database()

async def get_database():
    return db.db