@echo off
echo Starting Video Summarizer Backend...
cd app
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
