import whisper
import torch
import os
from typing import Dict, List, Optional
import tempfile
import numpy as np

class WhisperTranscriber:
    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper model
        model_size: "tiny", "base", "small", "medium", "large"
        """
        print(f"Loading Whisper {model_size} model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(model_size).to(self.device)
        print(f"Whisper model loaded on {self.device}")
    
    def transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe audio file
        """
        try:
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False,
                language=None  # Auto-detect language
            )
            
            return {
                'text': result['text'],
                'segments': result['segments'],
                'language': result['language'],
                'duration': result.get('segments', [{}])[-1].get('end', 0) if result.get('segments') else 0
            }
            
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")
    
    def transcribe_file(self, video_path: str) -> Dict:
        """
        Extract audio from video and transcribe
        """
        try:
            # Extract audio using moviepy
            import moviepy.editor as mp
            
            # Create temp audio file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                audio_path = tmp.name
            
            # Extract audio
            video = mp.VideoFileClip(video_path)
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)
            video.close()
            
            # Transcribe
            result = self.transcribe(audio_path)
            
            # Clean up
            os.unlink(audio_path)
            
            return result
            
        except Exception as e:
            raise Exception(f"Audio extraction/transcription failed: {str(e)}")
    
    def get_segments(self, video_path: str) -> List[Dict]:
        """
        Get transcribed segments with timestamps
        """
        result = self.transcribe_file(video_path)
        
        segments = []
        for segment in result['segments']:
            segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'],
                'confidence': np.mean([word.get('probability', 0.8) for word in segment.get('words', [])]) if segment.get('words') else 0.8
            })
        
        return segments

# Test the model
if __name__ == "__main__":
    transcriber = WhisperTranscriber("tiny")  # Use tiny for testing
    print("Whisper model ready!")
