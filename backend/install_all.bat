@echo off
echo Installing AI Video Summarizer Dependencies...
echo.

echo Step 1: Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Step 2: Installing setuptools and wheel...
pip install setuptools==69.0.3 wheel==0.42.0

echo.
echo Step 3: Installing build tools...
pip install build cython

echo.
echo Step 4: Installing core ML packages...
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu

echo.
echo Step 5: Installing faster-whisper (alternative to openai-whisper)...
pip install faster-whisper

echo.
echo Step 6: Installing other ML packages...
pip install transformers==4.46.0
pip install sentence-transformers==3.3.1

echo.
echo Step 7: Installing video processing packages...
pip install moviepy==1.0.3
pip install opencv-python-headless==4.10.0.84
pip install Pillow==11.0.0

echo.
echo Step 8: Installing scientific packages...
pip install numpy==1.26.4
pip install scipy==1.14.1

echo.
echo Step 9: Installing audio processing...
pip install ffmpeg-python soundfile librosa

echo.
echo Step 10: Installing web framework...
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 python-multipart==0.0.6 python-dotenv==1.0.0

echo.
echo Installation complete!
echo.
echo To start the server, run: uvicorn app.main:app --reload
