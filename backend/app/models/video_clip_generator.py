from moviepy.editor import VideoFileClip, concatenate_videoclips
from typing import List, Dict
import os

class VideoClipGenerator:
    def __init__(self):
        pass
    
    def generate_summary_video(self, video_path: str, segments: List[Dict], output_path: str) -> str:
        """Generate summarized video from selected segments using moviepy"""
        try:
            # Load the original video
            video = VideoFileClip(video_path)
            
            # Extract clips based on segments
            clips = []
            for segment in segments:
                start = segment.get('start', 0)
                end = segment.get('end', start + 5)  # Default 5 sec if no end
                
                # Extract clip
                clip = video.subclip(start, end)
                clips.append(clip)
            
            # Concatenate all clips
            if clips:
                final_video = concatenate_videoclips(clips, method="compose")
                
                # Write output
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True
                )
                
                # Close clips
                final_video.close()
                video.close()
                
                return output_path
            else:
                video.close()
                return None
                
        except Exception as e:
            print(f"Video generation error: {e}")
            return None
