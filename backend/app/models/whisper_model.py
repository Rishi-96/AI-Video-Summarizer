"""
whisper_model.py — Groq API transcription with chunked audio processing
to reduce peak memory usage and fit within Groq API constraints.
"""
import logging
import os
import tempfile
from typing import Dict, List

import numpy as np
import soundfile as sf

from app.core.constants import WHISPER_MODEL_NAME, AUDIO_CHUNK_SECONDS

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False
    logger.warning("groq not installed; WhisperTranscriber unavailable")


class WhisperTranscriber:
    def __init__(self, model_size: str = WHISPER_MODEL_NAME, chunk_seconds: int = AUDIO_CHUNK_SECONDS):
        """
        Args:
            model_size:    Ignored locally, maps directly to Groq's whisper-large-v3
            chunk_seconds: audio chunk length in seconds (Groq max is ~25mb)
        """
        self.chunk_seconds = chunk_seconds
        
        from app.core.config import settings
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        self.use_mock = not _HAS_GROQ or not self.api_key
        
        if not self.use_mock:
            try:
                import httpx
                _disable_ssl = os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true"
                http_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
                http_client = httpx.Client(
                    proxy=http_proxy,
                    verify=not _disable_ssl,
                )
                self.client = Groq(api_key=self.api_key, http_client=http_client)
                logger.info("Groq Whisper Transcriber loaded")
            except Exception as e:
                logger.warning("Error initializing Groq Whisper: %s", e)
                self.use_mock = True
        else:
            logger.warning("GROQ_API_KEY missing or groq not installed. Falling back to mock transcription.")


    # ------------------------------------------------------------------
    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe a single audio file via Groq."""
        if self.use_mock:
            return {
                "text": "This is a mock transcription because Groq wasn't configured.",
                "segments": [{"text": "Mock.", "start": 0, "end": 2, "words": []}],
                "duration": 2
            }
            
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio_file.read()),
                    model=WHISPER_MODEL_NAME,
                    response_format="verbose_json",
                )
            
            # Groq 'verbose_json' sometimes returns a dict vs object depending on sdk ver
            segments_raw = getattr(transcription, "segments", [])
            if not segments_raw and isinstance(transcription, dict):
                segments_raw = transcription.get("segments", [])
                
            segments = []
            for seg in segments_raw:
                if isinstance(seg, dict):
                    segments.append(seg)
                else:
                    segments.append({
                        "start": getattr(seg, "start", 0),
                        "end": getattr(seg, "end", 0),
                        "text": getattr(seg, "text", ""),
                        "words": getattr(seg, "words", []) or []
                    })
                    
            text = getattr(transcription, "text", "")
            if isinstance(transcription, dict):
                text = transcription.get("text", "")
                
            duration = segments[-1]["end"] if segments else getattr(transcription, "duration", 0)

            return {
                "text": text,
                "segments": segments,
                "language": "en",
                "duration": duration,
            }
        except Exception as e:
            raise RuntimeError(f"Groq Transcription failed: {e}") from e

    # ------------------------------------------------------------------
    def _extract_audio(self, video_path: str) -> str:
        """Extract audio to a temporary WAV file using fast ffmpeg. Caller must delete it."""
        from app.core.audio import extract_audio_fast
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        audio_path = tmp.name
        tmp.close()
        return extract_audio_fast(video_path, audio_path)

    # ------------------------------------------------------------------
    def _chunk_audio(self, audio_path: str) -> List[str]:
        """
        Split an audio file into fixed-length chunks to limit API size caps.
        Returns a list of temporary WAV file paths.
        """
        try:
            data, samplerate = sf.read(audio_path)
        except Exception:
            return [audio_path]

        chunk_samples = self.chunk_seconds * samplerate
        total_samples = len(data)
        chunk_paths = []

        for start in range(0, total_samples, chunk_samples):
            chunk = data[start : start + chunk_samples]
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            sf.write(tmp.name, chunk, samplerate)
            chunk_paths.append(tmp.name)

        return chunk_paths if chunk_paths else [audio_path]

    # ------------------------------------------------------------------
    def transcribe_file(self, video_path: str) -> Dict:
        """Extract audio from video, chunk it, transcribe each chunk, merge results."""
        audio_path = self._extract_audio(video_path)
        chunk_paths = self._chunk_audio(audio_path)

        all_text = []
        all_segments = []
        total_offset = 0.0

        try:
            for chunk_path in chunk_paths:
                result = self.transcribe(chunk_path)
                all_text.append(result["text"])

                for seg in result["segments"]:
                    seg_copy = dict(seg)
                    seg_copy["start"] += total_offset
                    seg_copy["end"]   += total_offset
                    all_segments.append(seg_copy)

                if result["segments"]:
                    total_offset = all_segments[-1]["end"]
        finally:
            for p in chunk_paths:
                if p != audio_path and os.path.exists(p):
                    os.unlink(p)
            if os.path.exists(audio_path):
                os.unlink(audio_path)

        return {
            "text":     " ".join(all_text),
            "segments": all_segments,
            "language": "auto",
            "duration": all_segments[-1]["end"] if all_segments else 0,
        }

    # ------------------------------------------------------------------
    def get_segments(self, video_path: str) -> List[Dict]:
        """High-level: transcribe a video and return enriched segment list."""
        result = self.transcribe_file(video_path)
        segments = []
        for seg in result["segments"]:
            words = seg.get("words", [])
            confidence = 0.99
            if words:
                 # Calculate avg probability if provided by groq
                 probs = [getattr(w, 'probability', 0.99) if not isinstance(w, dict) else w.get("probability", 0.99) for w in words]
                 confidence = float(np.mean(probs))
            
            segments.append({
                "start":      seg.get("start", 0),
                "end":        seg.get("end", 0),
                "text":       seg.get("text", ""),
                "confidence": confidence,
            })
        return segments
