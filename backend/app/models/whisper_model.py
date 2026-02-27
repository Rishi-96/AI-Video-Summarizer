"""
whisper_model.py — OpenAI Whisper transcription with chunked audio processing
to reduce peak memory usage on large files.
"""
import logging
import os
import tempfile
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import whisper
    import torch
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False
    logger.warning("whisper / torch not installed; WhisperTranscriber unavailable")


class WhisperTranscriber:
    def __init__(self, model_size: str = "base", chunk_seconds: int = 30):
        """
        Args:
            model_size:    tiny | base | small | medium | large
            chunk_seconds: audio chunk length in seconds (lower = less peak RAM)
        """
        if not _HAS_WHISPER:
            raise RuntimeError("whisper and torch are required. Install them via requirements.txt.")

        self.chunk_seconds = chunk_seconds
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading Whisper '%s' model on %s …", model_size, self.device)
        self.model = whisper.load_model(model_size).to(self.device)
        logger.info("Whisper model loaded")

    # ------------------------------------------------------------------
    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe a single audio file and return structured result."""
        try:
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False,
                language=None,
            )
            segments = result.get("segments", [])
            return {
                "text":     result["text"],
                "segments": segments,
                "language": result.get("language", "en"),
                "duration": segments[-1].get("end", 0) if segments else 0,
            }
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}") from e

    # ------------------------------------------------------------------
    def _extract_audio(self, video_path: str) -> str:
        """Extract audio to a temporary WAV file. Caller must delete it."""
        try:
            import moviepy.editor as mp  # lazy import — heavy
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            audio_path = tmp.name
            tmp.close()

            clip = mp.VideoFileClip(video_path)
            clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            clip.close()
            return audio_path
        except Exception as e:
            raise RuntimeError(f"Audio extraction failed: {e}") from e

    # ------------------------------------------------------------------
    def _chunk_audio(self, audio_path: str) -> List[str]:
        """
        Split an audio file into fixed-length chunks to limit peak memory.
        Returns a list of temporary WAV file paths.
        """
        try:
            import soundfile as sf
            data, samplerate = sf.read(audio_path)
        except Exception:
            # soundfile not available — fall back to single chunk
            return [audio_path]

        chunk_samples = self.chunk_seconds * samplerate
        total_samples = len(data)
        chunk_paths = []

        for start in range(0, total_samples, chunk_samples):
            chunk = data[start : start + chunk_samples]
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            import soundfile as sf2
            sf2.write(tmp.name, chunk, samplerate)
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
            # Clean up chunk temp files (but not if it's the original audio)
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
            confidence = float(np.mean([w.get("probability", 0.8) for w in words])) if words else 0.8
            segments.append({
                "start":      seg["start"],
                "end":        seg["end"],
                "text":       seg["text"],
                "confidence": confidence,
            })
        return segments
