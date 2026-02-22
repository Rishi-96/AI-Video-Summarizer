@echo off
echo ========================================
echo MongoDB Installation Guide
echo ========================================
echo.
echo Option 1: Install MongoDB Community Server
echo Download from: https://www.mongodb.com/try/download/community
echo Choose: Windows x64, MSI installer
echo.
echo Option 2: Use MongoDB Atlas (Cloud - Free)
echo Sign up at: https://www.mongodb.com/cloud/atlas/register
echo.
echo Option 3: Use Docker
echo Run: docker run -d -p 27017:27017 --name mongodb mongo:latest
echo.
echo ========================================
echo After installation, MongoDB will run on:
echo mongodb://localhost:27017
echo ========================================
pause
