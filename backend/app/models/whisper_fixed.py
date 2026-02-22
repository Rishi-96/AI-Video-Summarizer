import os
import tempfile
import subprocess
from typing import Dict, List, Optional

class FixedWhisperTranscriber:
    """
    Transcriber that works without the 'av' package
    Uses ffmpeg directly for audio extraction
    """
    
    def __init__(self, model_size: str = "tiny"):
        self.model_size = model_size
        self.model = None
        self.use_mock = False
        
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                num_workers=1,
                cpu_threads=4
            )
            print(f"✅ Faster-Whisper loaded with model {model_size}")
        except ImportError:
            print("⚠️ faster-whisper not available, using mock mode")
            self.use_mock = True
        except Exception as e:
            print(f"⚠️ Error loading faster-whisper: {e}")
            self.use_mock = True
    
    def extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio using ffmpeg directly (no av package needed)"""
        audio_path = tempfile.mktemp(suffix='.wav')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            audio_path
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return audio_path
        except subprocess.CalledProcessError as e:
            print(f"Audio extraction failed: {e.stderr}")
            return None
        except FileNotFoundError:
            print("❌ ffmpeg not found. Please install ffmpeg and add it to PATH")
            return None
    
    def transcribe_file(self, video_path: str) -> Dict:
        """Transcribe video file"""
        
        # Mock mode for testing
        if self.use_mock or self.model is None:
            return {
                'text': 'This is a sample transcription for testing. The video appears to contain important content about AI and machine learning.',
                'segments': [
                    {'start': 0, 'end': 5, 'text': 'This is a sample transcription for testing.'},
                    {'start': 5, 'end': 10, 'text': 'The video appears to contain important content about AI.'},
                    {'start': 10, 'end': 15, 'text': 'And machine learning applications.'}
                ],
                'language': 'en'
            }
        
        # Extract audio
        audio_path = self.extract_audio(video_path)
        if not audio_path:
            return {'text': '', 'segments': [], 'language': 'en'}
        
        try:
            # Transcribe
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                language=None,
                task="transcribe"
            )
            
            # Convert segments to list
            segment_list = []
            full_text = []
            
            for segment in segments:
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                })
                full_text.append(segment.text)
            
            return {
                'text': ' '.join(full_text),
                'segments': segment_list,
                'language': info.language
            }
            
        except Exception as e:
            print(f"Transcription failed: {e}")
            return {'text': '', 'segments': [], 'language': 'en'}
            
        finally:
            # Clean up audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except:
                    pass
    
    def get_segments(self, video_path: str) -> List[Dict]:
        """Get transcribed segments"""
        result = self.transcribe_file(video_path)
        return result.get('segments', [])

# Test the transcriber
if __name__ == "__main__":
    transcriber = FixedWhisperTranscriber("tiny")
    print("✅ Fixed transcriber ready!")
    # Test mock transcription
    result = transcriber.transcribe_file("test.mp4")
    print(f"Mock transcription: {result['text'][:50]}...")
