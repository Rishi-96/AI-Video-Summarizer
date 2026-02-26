@echo off
echo ========================================
echo   AI Video Summarizer - Starting Servers
echo ========================================
echo.

echo [1/2] Starting Backend (port 8000)...
cd /d "c:\Users\Himani Jain\Documents\MajorProject\AI-Video-Summarizer\backend"
start "Backend Server" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [2/2] Starting Frontend (port 3000)...
cd /d "c:\Users\Himani Jain\Documents\MajorProject\AI-Video-Summarizer\frontend"
start "Frontend Server" cmd /k "set HOST=0.0.0.0 && npm start"

echo.
echo Both servers starting in new windows!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
pause
