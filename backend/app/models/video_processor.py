"""
video_processor.py — Visual summary video generator.

Creates a short, slideshow-style summary video from a long video by:
  1. Extracting key frames spread evenly across the video
  2. Overlaying the AI-generated summary text and key points
  3. Adding smooth fade transitions between slides
  4. Producing a compact MP4 that communicates the full content quickly
"""
import logging
import os
import textwrap
import tempfile
from typing import Dict, List, Optional

import cv2
try:
    import moviepy.editor as mp
except ImportError:
    import moviepy as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
FPS = 24
FADE_DURATION = 0.5          # seconds of cross-fade between slides
TITLE_SLIDE_DURATION = 4     # seconds
KEY_FRAME_DURATION = 5       # seconds per key-frame slide
KEY_POINT_DURATION = 4       # seconds per key-point slide
CLOSING_SLIDE_DURATION = 3   # seconds

# Colours (RGB)
BG_DARK = (15, 17, 26)
ACCENT_BLUE = (59, 130, 246)
ACCENT_PURPLE = (139, 92, 246)
TEXT_WHITE = (255, 255, 255)
TEXT_GREY = (180, 180, 195)
OVERLAY_COLOR = (10, 12, 22)


class VideoProcessor:
    def __init__(self):
        logger.info("Video processor initialized")
        self._font_cache: dict = {}

    # ------------------------------------------------------------------
    # Font helpers
    # ------------------------------------------------------------------
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Return a PIL font; fall back to the default if no TTF is found."""
        key = (size, bold)
        if key in self._font_cache:
            return self._font_cache[key]

        # Try common system font paths
        candidates = [
            # Windows
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
        ]

        for path in candidates:
            if path and os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    self._font_cache[key] = font
                    return font
                except Exception:
                    continue

        font = ImageFont.load_default()
        self._font_cache[key] = font
        return font

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius, fill):
        """Draw a rounded rectangle on a PIL ImageDraw."""
        x0, y0, x1, y1 = xy
        draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
        draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
        draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=fill)
        draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=fill)
        draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=fill)
        draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=fill)

    def _add_gradient_overlay(self, img: Image.Image, opacity: int = 180) -> Image.Image:
        """Add a bottom-to-top gradient dark overlay for text readability."""
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = img.size
        # Gradient from bottom (opaque) to ~60% up (transparent)
        gradient_start = int(h * 0.35)
        for y in range(gradient_start, h):
            progress = (y - gradient_start) / (h - gradient_start)
            alpha = int(opacity * progress)
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        return Image.alpha_composite(img.convert("RGBA"), overlay)

    # ------------------------------------------------------------------
    # Slide generators
    # ------------------------------------------------------------------
    def _create_title_slide(self, title: str, duration_str: str) -> np.ndarray:
        """Create a stylish title slide."""
        img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), BG_DARK)
        draw = ImageDraw.Draw(img)

        # Decorative gradient bar at top
        for y in range(6):
            # Interpolate blue → purple
            r = int(ACCENT_BLUE[0] + (ACCENT_PURPLE[0] - ACCENT_BLUE[0]) * y / 5)
            g = int(ACCENT_BLUE[1] + (ACCENT_PURPLE[1] - ACCENT_BLUE[1]) * y / 5)
            b = int(ACCENT_BLUE[2] + (ACCENT_PURPLE[2] - ACCENT_BLUE[2]) * y / 5)
            draw.line([(0, y), (OUTPUT_WIDTH, y)], fill=(r, g, b))

        # "AI VIDEO SUMMARY" label
        label_font = self._get_font(18, bold=True)
        label_text = "AI VIDEO SUMMARY"
        label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
        label_w = label_bbox[2] - label_bbox[0]
        label_x = (OUTPUT_WIDTH - label_w) // 2
        label_y = 220

        # Pill background for label
        pill_pad_x, pill_pad_y = 20, 8
        self._draw_rounded_rect(
            draw,
            (label_x - pill_pad_x, label_y - pill_pad_y,
             label_x + label_w + pill_pad_x, label_y + 20 + pill_pad_y),
            radius=14,
            fill=ACCENT_BLUE,
        )
        draw.text((label_x, label_y), label_text, font=label_font, fill=TEXT_WHITE)

        # Title
        title_font = self._get_font(42, bold=True)
        wrapped = textwrap.fill(title[:120], width=36)
        title_bbox = draw.multiline_textbbox((0, 0), wrapped, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        title_h = title_bbox[3] - title_bbox[1]
        title_x = (OUTPUT_WIDTH - title_w) // 2
        title_y = 300
        draw.multiline_text((title_x, title_y), wrapped, font=title_font, fill=TEXT_WHITE, align="center")

        # Duration info
        if duration_str:
            info_font = self._get_font(22)
            info_text = f"Original Duration: {duration_str}"
            info_bbox = draw.textbbox((0, 0), info_text, font=info_font)
            info_w = info_bbox[2] - info_bbox[0]
            draw.text(((OUTPUT_WIDTH - info_w) // 2, title_y + title_h + 50), info_text, font=info_font, fill=TEXT_GREY)

        # Bottom decorative line
        for y in range(OUTPUT_HEIGHT - 4, OUTPUT_HEIGHT):
            draw.line([(0, y), (OUTPUT_WIDTH, y)], fill=ACCENT_PURPLE)

        return np.array(img)

    def _create_frame_slide(self, frame: np.ndarray, text: str, slide_num: int, total_slides: int) -> np.ndarray:
        """Create a slide with a key frame as background and summary text overlaid."""
        # Resize frame to output dimensions
        pil_frame = Image.fromarray(frame).resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.LANCZOS)

        # Add gradient overlay for text readability
        pil_frame = self._add_gradient_overlay(pil_frame, opacity=200)
        pil_frame = pil_frame.convert("RGB")
        draw = ImageDraw.Draw(pil_frame)

        # Wrap text — allow up to 7 lines to show more content
        text_font = self._get_font(24)
        wrapped = textwrap.fill(text.strip(), width=65)
        lines = wrapped.split("\n")
        if len(lines) > 7:
            lines = lines[:7]
            lines[-1] = lines[-1][:75] + "..."
        wrapped = "\n".join(lines)

        # Draw text container at bottom
        text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=text_font)
        text_h = text_bbox[3] - text_bbox[1]
        pad = 30
        container_y = OUTPUT_HEIGHT - text_h - pad * 2 - 50

        # Semi-transparent container background
        container_img = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
        container_draw = ImageDraw.Draw(container_img)
        self._draw_rounded_rect(
            container_draw,
            (40, container_y, OUTPUT_WIDTH - 40, OUTPUT_HEIGHT - 30),
            radius=16,
            fill=(10, 12, 22, 200),
        )
        pil_frame = Image.alpha_composite(pil_frame.convert("RGBA"), container_img).convert("RGB")
        draw = ImageDraw.Draw(pil_frame)

        # Draw text
        draw.multiline_text(
            (70, container_y + pad),
            wrapped,
            font=text_font,
            fill=TEXT_WHITE,
            spacing=8,
        )

        # Slide counter (top right)
        counter_font = self._get_font(16)
        counter_text = f"{slide_num}/{total_slides}"
        counter_bbox = draw.textbbox((0, 0), counter_text, font=counter_font)
        counter_w = counter_bbox[2] - counter_bbox[0]
        self._draw_rounded_rect(
            draw,
            (OUTPUT_WIDTH - counter_w - 40, 18, OUTPUT_WIDTH - 20, 44),
            radius=10,
            fill=(0, 0, 0),
        )
        draw.text((OUTPUT_WIDTH - counter_w - 30, 20), counter_text, font=counter_font, fill=TEXT_GREY)

        return np.array(pil_frame)

    def _create_keypoint_slide(self, points: List[str], start_idx: int, end_idx: int) -> np.ndarray:
        """Create a styled slide showing key points."""
        img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), BG_DARK)
        draw = ImageDraw.Draw(img)

        # Header
        header_font = self._get_font(34, bold=True)
        draw.text((80, 60), "📌 Key Points", font=header_font, fill=TEXT_WHITE)

        # Accent line under header
        draw.rectangle([(80, 110), (300, 114)], fill=ACCENT_BLUE)

        # Points
        point_font = self._get_font(24)
        y_offset = 150
        for i in range(start_idx, min(end_idx, len(points))):
            point = points[i]
            # Number badge
            badge_text = str(i + 1)
            badge_font = self._get_font(18, bold=True)
            self._draw_rounded_rect(
                draw,
                (80, y_offset, 116, y_offset + 36),
                radius=8,
                fill=ACCENT_PURPLE,
            )
            badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
            badge_w = badge_bbox[2] - badge_bbox[0]
            draw.text((98 - badge_w // 2, y_offset + 6), badge_text, font=badge_font, fill=TEXT_WHITE)

            # Point text
            wrapped = textwrap.fill(point[:200], width=55)
            draw.multiline_text((140, y_offset + 4), wrapped, font=point_font, fill=TEXT_WHITE, spacing=6)

            # Calculate height
            pbbox = draw.multiline_textbbox((0, 0), wrapped, font=point_font)
            p_h = pbbox[3] - pbbox[1]
            y_offset += max(50, p_h + 30)

        return np.array(img)

    def _create_closing_slide(self) -> np.ndarray:
        """Create a closing/end slide."""
        img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), BG_DARK)
        draw = ImageDraw.Draw(img)

        # "Summary Complete" text
        title_font = self._get_font(40, bold=True)
        text = "Summary Complete ✓"
        bbox = draw.textbbox((0, 0), text, font=title_font)
        tw = bbox[2] - bbox[0]
        draw.text(((OUTPUT_WIDTH - tw) // 2, 280), text, font=title_font, fill=TEXT_WHITE)

        # Subtitle
        sub_font = self._get_font(22)
        sub = "Generated by AI Video Summarizer"
        sbbox = draw.textbbox((0, 0), sub, font=sub_font)
        sw = sbbox[2] - sbbox[0]
        draw.text(((OUTPUT_WIDTH - sw) // 2, 350), sub, font=sub_font, fill=TEXT_GREY)

        # Decorative gradient line
        line_y = 420
        line_w = 300
        line_x = (OUTPUT_WIDTH - line_w) // 2
        for x in range(line_x, line_x + line_w):
            progress = (x - line_x) / line_w
            r = int(ACCENT_BLUE[0] + (ACCENT_PURPLE[0] - ACCENT_BLUE[0]) * progress)
            g = int(ACCENT_BLUE[1] + (ACCENT_PURPLE[1] - ACCENT_BLUE[1]) * progress)
            b = int(ACCENT_BLUE[2] + (ACCENT_PURPLE[2] - ACCENT_BLUE[2]) * progress)
            for dy in range(3):
                draw.point((x, line_y + dy), fill=(r, g, b))

        return np.array(img)

    # ------------------------------------------------------------------
    # Public API: basic utilities (unchanged)
    # ------------------------------------------------------------------
    def get_video_info(self, video_path: str) -> Dict:
        """Get video metadata."""
        video = mp.VideoFileClip(video_path)
        info = {
            'duration': video.duration,
            'fps': video.fps,
            'size': video.size,
            'width': video.w,
            'height': video.h,
            'audio': video.audio is not None,
        }
        video.close()
        return info

    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """Extract audio from video."""
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.wav')
        video = mp.VideoFileClip(video_path)
        video.audio.write_audiofile(output_path)
        video.close()
        return output_path

    def extract_frames(self, video_path: str, num_frames: int = 10) -> List[np.ndarray]:
        """Extract key frames from video evenly spread.
        
        Returns list of tuples: (frame_rgb_array, timestamp_seconds).
        """
        results = []
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        if total_frames <= 0:
            cap.release()
            return results

        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = float(idx) / fps
                results.append((frame_rgb, timestamp))
        cap.release()
        return results

    # ------------------------------------------------------------------
    # Old segment-stitching method (kept for backward compat)
    # ------------------------------------------------------------------
    def create_summary_video(self, video_path: str, segments: List[Dict], output_path: str):
        """Create summary video from selected segments (clip-based)."""
        try:
            video = mp.VideoFileClip(video_path)
            clips = []
            for segment in segments:
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                if end > start:
                    clip = video.subclip(start, end)
                    clips.append(clip)
            if clips:
                final_video = mp.concatenate_videoclips(clips, method="compose")
                final_video.write_videofile(
                    output_path, codec='libx264', audio_codec='aac',
                    temp_audiofile='temp-audio.m4a', remove_temp=True
                )
                final_video.close()
            video.close()
            return output_path
        except Exception as e:
            logger.error(f"Highlight video creation failed: {e}")
            raise Exception(f"Video creation failed: {str(e)}")

    def create_highlight_video(self, video_path: str, segments: List[Dict], output_path: str, title: str = "Highlights"):
        """
        Create a high-quality highlight reel with title overlay.
        This is a more premium version of create_summary_video.
        """
        try:
            source = mp.VideoFileClip(video_path)
            
            # 1. Title Slide (3s)
            title_img = self._create_title_slide(title, self._format_duration(source.duration))
            title_clip = mp.ImageClip(title_img).set_duration(3).crossfadeout(0.5)
            
            # 2. Clips
            clips = [title_clip]
            for i, seg in enumerate(segments[:12]): # limit to 12 clips max
                start, end = seg['start'], seg['end']
                if end - start < 1.0: continue # Skip too short
                
                clip = source.subclip(start, end).crossfadein(0.3).crossfadeout(0.3)
                clips.append(clip)
            
            # 3. Closing
            closing_img = self._create_closing_slide()
            closing_clip = mp.ImageClip(closing_img).set_duration(2).crossfadein(0.5)
            clips.append(closing_clip)
            
            # 4. Concatenate
            final = mp.concatenate_videoclips(clips, method="compose", padding=-0.3)
            
            # 5. Write
            final.write_videofile(
                output_path, codec='libx264', audio_codec='aac',
                fps=FPS, preset="medium",
                temp_audiofile='temp-audio.m4a', remove_temp=True
            )
            
            final.close()
            source.close()
            return output_path
        except Exception as e:
            logger.error(f"Highlight reel generation failed: {e}")
            # Fallback to simple concatenation if fancy fails
            return self.create_summary_video(video_path, segments, output_path)


    # ------------------------------------------------------------------
    # NEW: Visual summary video
    # ------------------------------------------------------------------
    def create_visual_summary(
        self,
        video_path: str,
        text_summary: str,
        key_points: List[str],
        output_path: str,
        video_title: str = "Video Summary",
        num_key_frames: int = 0,  # 0 = auto-calculate based on text
    ) -> str:
        """
        Create a short visual summary video from background key-frames
        overlaid with the AI-generated summary text and key points.

        The number of slides adapts to the text length so that ALL
        summary content is included — nothing is cut off.

        Audio is extracted from the original video at each key frame's
        timestamp so the viewer hears the speaker's voice matching
        each slide.

        Structure:
          1. Title slide (4s)  — silence
          2. Key-frame slides with summary text (5s each) — original audio
          3. Key-point slides (4s each) — silence
          4. Closing slide (3s) — silence

        Returns the output path.
        """
        logger.info("Creating visual summary: extracting key frames from %s", video_path)

        # ── 1. Gather video metadata & audio ──────────────────────────
        source_video = mp.VideoFileClip(video_path)
        video_duration = source_video.duration
        has_audio = source_video.audio is not None
        duration_str = self._format_duration(video_duration)

        # ── 2. Split summary text into sentence chunks FIRST ──────────
        #    Each chunk ~280 chars (fits ~7 lines at width 65)
        text_chunks = self._split_text_for_slides(text_summary, max_chars_per_slide=280)

        # Determine how many key frames we need (one per text chunk)
        if num_key_frames <= 0:
            num_key_frames = max(6, len(text_chunks))
        num_key_frames = min(num_key_frames, 25)
        if len(text_chunks) > num_key_frames:
            num_key_frames = len(text_chunks)

        # ── 3. Extract key frames with timestamps ─────────────────────
        frame_data = self.extract_frames(video_path, num_key_frames)
        if not frame_data:
            source_video.close()
            raise RuntimeError("Could not extract any frames from the video")

        frames = [fd[0] for fd in frame_data]
        timestamps = [fd[1] for fd in frame_data]

        # Pad text chunks or recycle frames to match counts
        while len(text_chunks) < len(frames):
            text_chunks.append("")
        original_frame_count = len(frames)
        while len(frames) < len(text_chunks):
            idx = len(frames) % original_frame_count
            frames.append(frames[idx])
            timestamps.append(timestamps[idx])

        # ── 4. Build visual slides ────────────────────────────────────
        #   Each entry: (numpy_image, duration_secs, is_keyframe, keyframe_idx)
        slides = []

        # Title slide
        title_img = self._create_title_slide(video_title, duration_str)
        slides.append((title_img, TITLE_SLIDE_DURATION, False, -1))

        # Key-frame + text slides
        total_frame_slides = len(frames)
        for i, frame in enumerate(frames):
            text_chunk = text_chunks[i] if i < len(text_chunks) else ""
            if not text_chunk.strip() and i >= len(text_chunks):
                continue
            slide_img = self._create_frame_slide(frame, text_chunk, i + 1, total_frame_slides)
            slides.append((slide_img, KEY_FRAME_DURATION, True, i))

        # Key-point slides
        if key_points:
            points_per_slide = 3
            for start in range(0, len(key_points), points_per_slide):
                end = start + points_per_slide
                kp_img = self._create_keypoint_slide(key_points, start, end)
                slides.append((kp_img, KEY_POINT_DURATION, False, -1))

        # Closing slide
        closing_img = self._create_closing_slide()
        slides.append((closing_img, CLOSING_SLIDE_DURATION, False, -1))

        # ── 5. Build audio track ──────────────────────────────────────
        audio_clips = []
        if has_audio:
            logger.info("Extracting audio snippets from original video for %d slides", len(slides))
            for (_, slide_dur, is_kf, kf_idx) in slides:
                if is_kf and kf_idx >= 0:
                    # Extract audio from the original video around this frame's timestamp
                    ts = timestamps[kf_idx]
                    audio_start = max(0.0, ts)
                    audio_end = min(video_duration, ts + slide_dur)
                    actual_len = audio_end - audio_start

                    if actual_len > 0.5:
                        try:
                            audio_snippet = source_video.audio.subclip(audio_start, audio_end)
                            # If the snippet is shorter than the slide, pad with silence using vol(0)
                            if actual_len < slide_dur:
                                pad_len = slide_dur - actual_len
                                # Grab a snippet from the start and mute it
                                safe_pad_len = min(pad_len, video_duration)
                                silence = source_video.audio.subclip(0, safe_pad_len).volumex(0)
                                if safe_pad_len < pad_len:  # Extemely rare (video < slide diff)
                                    num_repeats = int(pad_len / safe_pad_len) + 1
                                    silence = mp.concatenate_audioclips([silence] * num_repeats).subclip(0, pad_len)
                                audio_snippet = mp.concatenate_audioclips([audio_snippet, silence])
                            else:
                                # Trim to exact slide duration
                                audio_snippet = audio_snippet.subclip(0, slide_dur)
                            audio_clips.append(audio_snippet)
                            continue
                        except Exception as e:
                            logger.debug("Audio extraction failed at %.1f: %s", ts, e)

                # Silence for non-keyframe slides or when audio extraction fails
                try:
                    if has_audio and video_duration > 0.1:
                        safe_dur = min(slide_dur, video_duration)
                        silence = source_video.audio.subclip(0, safe_dur).volumex(0)
                        if safe_dur < slide_dur:
                            num_repeats = int(slide_dur / safe_dur) + 1
                            silence = mp.concatenate_audioclips([silence] * num_repeats).subclip(0, slide_dur)
                        audio_clips.append(silence)
                except Exception as e:
                    logger.warning("Failed creating silence snippet: %s", e)


        # ── 6. Compose MoviePy clips with fade transitions ────────────
        logger.info("Composing %d slides into summary video", len(slides))
        faded_clips = []
        for (frame_arr, dur, _, _) in slides:
            clip = mp.ImageClip(frame_arr).set_duration(dur)
            clip = clip.crossfadein(FADE_DURATION).crossfadeout(FADE_DURATION)
            faded_clips.append(clip)

        final = mp.concatenate_videoclips(faded_clips, method="compose", padding=-FADE_DURATION)

        # Attach audio if available
        if audio_clips:
            try:
                combined_audio = mp.concatenate_audioclips(audio_clips)
                # Trim/pad audio to match final video duration
                if combined_audio.duration > final.duration:
                    combined_audio = combined_audio.subclip(0, final.duration)
                final = final.set_audio(combined_audio)
                logger.info("Audio track attached (%.1fs)", combined_audio.duration)
            except Exception as e:
                logger.warning("Failed to attach audio track (non-fatal): %s", e)

        # Write output
        write_kwargs = {
            "fps": FPS,
            "codec": "libx264",
            "preset": "medium"
        }
        if final.audio is not None:
            write_kwargs["audio_codec"] = "aac"
            write_kwargs["temp_audiofile"] = tempfile.mktemp(suffix=".m4a")
            write_kwargs["remove_temp"] = True
        else:
            write_kwargs["audio"] = False

        final.write_videofile(output_path, **write_kwargs)

        total_duration = sum(d for _, d, _, _ in slides) - FADE_DURATION * (len(slides) - 1)
        logger.info("Visual summary video created: %s (~%.0f seconds, %d slides)", output_path, total_duration, len(slides))
        final.close()
        source_video.close()
        return output_path

    # ------------------------------------------------------------------
    # Text splitting — ensures ALL text is included
    # ------------------------------------------------------------------
    @staticmethod
    def _split_text_for_slides(text: str, max_chars_per_slide: int = 280) -> List[str]:
        """
        Split summary text into chunks that each fit on a single slide.
        Guarantees ALL text is included across the returned chunks.
        """
        if not text or not text.strip():
            return [""]

        # Split into sentences
        sentences = []
        for s in text.replace("\n", " ").split(". "):
            s = s.strip()
            if s:
                sentences.append(s if s.endswith(".") else s + ".")

        if not sentences:
            # Fallback: split by character count
            chunks = []
            for i in range(0, len(text), max_chars_per_slide):
                chunks.append(text[i:i + max_chars_per_slide])
            return chunks if chunks else [text]

        # Group sentences into chunks that fit within max_chars_per_slide
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # If adding this sentence would exceed limit, start a new chunk
            if current_chunk and len(current_chunk) + len(sentence) + 1 > max_chars_per_slide:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk = (current_chunk + " " + sentence).strip()

        # Don't forget the last chunk!
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text[:max_chars_per_slide]]

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds into human-readable duration."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"


# Test the model
if __name__ == "__main__":
    processor = VideoProcessor()
    print("Video processor ready!")
