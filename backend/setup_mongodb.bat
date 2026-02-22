@echo off
echo ========================================
echo MongoDB Setup for Video Summarizer
echo ========================================
echo.

echo Step 1: Installing MongoDB (Choose one option)
echo.
echo Option A: Download MongoDB Community Server
echo URL: https://www.mongodb.com/try/download/community
echo - Choose Windows x64, MSI installer
echo - Install with default settings
echo - MongoDB will run on: mongodb://localhost:27017
echo.
echo Option B: Use Docker
echo Command: docker run -d -p 27017:27017 --name mongodb mongo:latest
echo.
echo Option C: Use MongoDB Atlas (Cloud - Free)
echo URL: https://www.mongodb.com/cloud/atlas/register
echo - Create free cluster
echo - Get connection string
echo - Update .env file with connection string
echo.
pause

echo.
echo Step 2: Verify MongoDB is running
echo.
mongosh --eval "db.version()" 2>nul
if %errorlevel% equ 0 (
    echo ✅ MongoDB is running!
) else (
    echo ❌ MongoDB is not running or not installed
    echo Please install MongoDB first
)
echo.

echo Step 3: Create database and collections
echo.
mongosh video_summarizer --eval "db.createCollection('users'); db.createCollection('videos'); db.createCollection('summaries'); db.createCollection('chat_sessions'); print('✅ Collections created');" 2>nul

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Your MongoDB is ready at: mongodb://localhost:27017
echo Database name: video_summarizer
echo.
echo Next: Start your FastAPI server
echo Command: uvicorn app.main:app --reload
echo.
pause
