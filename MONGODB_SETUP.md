# MongoDB Setup Guide

## Quick Setup (3 Options)

### Option 1: MongoDB Community Server (Recommended)
1. Download: https://www.mongodb.com/try/download/community
2. Choose: Windows x64, MSI installer
3. Install with default settings
4. MongoDB runs on: mongodb://localhost:27017

### Option 2: Docker (Fastest)
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### Option 3: MongoDB Atlas (Cloud - Free)
1. Sign up: https://www.mongodb.com/cloud/atlas/register
2. Create free cluster
3. Get connection string
4. Update .env: MONGODB_URL=your_connection_string

## Verify Installation

After installing, your app will automatically connect to MongoDB.

Start the server:
```bash
cd backend
uvicorn app.main:app --reload
```

Check logs for: "MongoDB connected"

## Database Structure

Database: video_summarizer
Collections:
- users (authentication)
- videos (uploaded files)
- summaries (AI results)
- chat_sessions (chat history)

All collections are created automatically on first use.
