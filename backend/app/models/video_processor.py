import moviepy.editor as mp
import cv2
import numpy as np
from typing import List, Dict, Optional
import os
from PIL import Image
import tempfile

class VideoProcessor:
    def __init__(self):
        print("Video processor initialized")
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        Get video metadata
        """
        video = mp.VideoFileClip(video_path)
        
        info = {
            'duration': video.duration,
            'fps': video.fps,
            'size': video.size,
            'width': video.w,
            'height': video.h,
            'audio': video.audio is not None
        }
        
        video.close()
        return info
    
    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """
        Extract audio from video
        """
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.wav')
        
        video = mp.VideoFileClip(video_path)
        video.audio.write_audiofile(output_path, verbose=False, logger=None)
        video.close()
        
        return output_path
    
    def extract_frames(self, video_path: str, num_frames: int = 10) -> List[np.ndarray]:
        """
        Extract key frames from video
        """
        frames = []
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames <= 0:
            return frames
        
        # Calculate frame indices to extract
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
        
        cap.release()
        return frames
    
    def create_summary_video(self, video_path: str, segments: List[Dict], output_path: str):
        """
        Create summary video from selected segments
        """
        try:
            video = mp.VideoFileClip(video_path)
            clips = []
            
            for i, segment in enumerate(segments):
                start_time = segment['start']
                end_time = segment['end']
                
                # Extract segment
                clip = video.subclip(start_time, end_time)
                clips.append(clip)
            
            # Concatenate clips
            if clips:
                final_video = mp.concatenate_videoclips(clips)
                
                # Write output
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    verbose=False,
                    logger=None
                )
                
                final_video.close()
            
            video.close()
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Video creation failed: {str(e)}")

# Test the model
if __name__ == "__main__":
    processor = VideoProcessor()
    print("Video processor ready!")
