import uvicorn
import os

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("processed", exist_ok=True)
    
    print("Starting AI Video Summarizer Backend...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
