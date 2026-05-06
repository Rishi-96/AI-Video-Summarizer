"""
video_processor.py — Visual summary video generator (MoviePy 2.x compatible).

Creates a summary video that is 40-50% of the original video's length by:
  1. Selecting the most important transcript segments (by AI relevance score)
  2. Stitching those clips back-to-back with the original audio
  3. Adding a title slide at the start and closing slide at the end
  4. Producing a compact MP4 that communicates the full content quickly
"""
import logging
import os
import textwrap
import tempfile
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    # MoviePy 2.x
    from moviepy import (
        VideoFileClip,
        ImageClip,
        CompositeVideoClip,
        concatenate_videoclips,
        ColorClip,
    )
    from moviepy.video.fx import FadeIn, FadeOut, CrossFadeIn, CrossFadeOut
    MOVIEPY_V2 = True
except ImportError:
    # Fallback: MoviePy 1.x
    import moviepy.editor as _mp
    VideoFileClip = _mp.VideoFileClip
    ImageClip = _mp.ImageClip
    CompositeVideoClip = _mp.CompositeVideoClip
    concatenate_videoclips = _mp.concatenate_videoclips
    ColorClip = _mp.ColorClip
    MOVIEPY_V2 = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
FPS = 24

# Summary target: produce a video that is 40-50% of the original duration
TARGET_RATIO_MIN = 0.40
TARGET_RATIO_MAX = 0.50
TARGET_RATIO = 0.45   # aim for 45% of original

TITLE_SLIDE_DURATION = 3.0   # seconds
CLOSING_SLIDE_DURATION = 2.0  # seconds
MIN_CLIP_DURATION = 1.5       # drop clips shorter than this

# Colours (RGB)
BG_DARK = (15, 17, 26)
ACCENT_BLUE = (59, 130, 246)
ACCENT_PURPLE = (139, 92, 246)
TEXT_WHITE = (255, 255, 255)
TEXT_GREY = (180, 180, 195)


# ---------------------------------------------------------------------------
# MoviePy 2.x compatibility helpers
# ---------------------------------------------------------------------------

def _set_duration(clip, duration: float):
    """Set clip duration — works in both MoviePy 1.x and 2.x."""
    if MOVIEPY_V2:
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _set_start(clip, start: float):
    """Set clip start time — works in both MoviePy 1.x and 2.x."""
    if MOVIEPY_V2:
        return clip.with_start(start)
    return clip.set_start(start)


def _resize_clip(clip, new_size: Tuple[int, int]):
    """Resize clip — API changed between MoviePy 1.x and 2.x."""
    if MOVIEPY_V2:
        return clip.resized(new_size)
    return clip.resize(newsize=new_size)


def _make_image_clip(arr: np.ndarray, duration: float):
    """Create an ImageClip from a numpy array with the given duration."""
    clip = ImageClip(arr)
    return _set_duration(clip, duration)


class VideoProcessor:
    def __init__(self):
        logger.info("Video processor initialized (MoviePy v2=%s)", MOVIEPY_V2)
        self._font_cache: dict = {}

    # ------------------------------------------------------------------
    # Font helpers
    # ------------------------------------------------------------------
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Return a PIL font; fall back to the default if no TTF is found."""
        key = (size, bold)
        if key in self._font_cache:
            return self._font_cache[key]

        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "",
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
        x0, y0, x1, y1 = xy
        draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
        draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
        draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=fill)
        draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=fill)
        draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=fill)
        draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=fill)

    # ------------------------------------------------------------------
    # Slide generators
    # ------------------------------------------------------------------
    def _create_title_slide(self, title: str, duration_str: str, summary_duration_str: str = "") -> np.ndarray:
        img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), BG_DARK)
        draw = ImageDraw.Draw(img)

        # Gradient top bar
        for y in range(8):
            r = int(ACCENT_BLUE[0] + (ACCENT_PURPLE[0] - ACCENT_BLUE[0]) * y / 7)
            g = int(ACCENT_BLUE[1] + (ACCENT_PURPLE[1] - ACCENT_BLUE[1]) * y / 7)
            b = int(ACCENT_BLUE[2] + (ACCENT_PURPLE[2] - ACCENT_BLUE[2]) * y / 7)
            draw.line([(0, y), (OUTPUT_WIDTH, y)], fill=(r, g, b))

        # Label pill
        label_font = self._get_font(22, bold=True)
        label_text = "AI VIDEO SUMMARY"
        label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
        label_w = label_bbox[2] - label_bbox[0]
        label_x = (OUTPUT_WIDTH - label_w) // 2
        label_y = 250
        pill_pad_x, pill_pad_y = 24, 10
        self._draw_rounded_rect(
            draw,
            (label_x - pill_pad_x, label_y - pill_pad_y,
             label_x + label_w + pill_pad_x, label_y + 26 + pill_pad_y),
            radius=16, fill=ACCENT_BLUE,
        )
        draw.text((label_x, label_y), label_text, font=label_font, fill=TEXT_WHITE)

        # Title
        title_font = self._get_font(52, bold=True)
        wrapped = textwrap.fill(title[:100], width=30)
        title_bbox = draw.multiline_textbbox((0, 0), wrapped, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        title_h = title_bbox[3] - title_bbox[1]
        draw.multiline_text(
            ((OUTPUT_WIDTH - title_w) // 2, 330),
            wrapped, font=title_font, fill=TEXT_WHITE, align="center",
        )

        # Duration info
        info_font = self._get_font(26)
        lines = []
        if duration_str:
            lines.append(f"Original: {duration_str}")
        if summary_duration_str:
            lines.append(f"Summary:  {summary_duration_str}  (~45%)")
        for i, line in enumerate(lines):
            info_bbox = draw.textbbox((0, 0), line, font=info_font)
            info_w = info_bbox[2] - info_bbox[0]
            draw.text(
                ((OUTPUT_WIDTH - info_w) // 2, 330 + title_h + 60 + i * 38),
                line, font=info_font, fill=TEXT_GREY,
            )

        # Bottom bar
        for y in range(OUTPUT_HEIGHT - 6, OUTPUT_HEIGHT):
            draw.line([(0, y), (OUTPUT_WIDTH, y)], fill=ACCENT_PURPLE)

        return np.array(img)

    def _create_closing_slide(self) -> np.ndarray:
        img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), BG_DARK)
        draw = ImageDraw.Draw(img)

        title_font = self._get_font(48, bold=True)
        text = "Summary Complete ✓"
        bbox = draw.textbbox((0, 0), text, font=title_font)
        tw = bbox[2] - bbox[0]
        draw.text(((OUTPUT_WIDTH - tw) // 2, 300), text, font=title_font, fill=TEXT_WHITE)

        sub_font = self._get_font(26)
        sub = "Generated by AI Video Summarizer"
        sbbox = draw.textbbox((0, 0), sub, font=sub_font)
        sw = sbbox[2] - sbbox[0]
        draw.text(((OUTPUT_WIDTH - sw) // 2, 390), sub, font=sub_font, fill=TEXT_GREY)

        line_y, line_w = 460, 400
        line_x = (OUTPUT_WIDTH - line_w) // 2
        for x in range(line_x, line_x + line_w):
            progress = (x - line_x) / line_w
            r = int(ACCENT_BLUE[0] + (ACCENT_PURPLE[0] - ACCENT_BLUE[0]) * progress)
            g = int(ACCENT_BLUE[1] + (ACCENT_PURPLE[1] - ACCENT_BLUE[1]) * progress)
            b = int(ACCENT_BLUE[2] + (ACCENT_PURPLE[2] - ACCENT_BLUE[2]) * progress)
            for dy in range(4):
                draw.point((x, line_y + dy), fill=(r, g, b))

        return np.array(img)

    # ------------------------------------------------------------------
    # Public API: basic utilities
    # ------------------------------------------------------------------
    def get_video_info(self, video_path: str) -> Dict:
        video = VideoFileClip(video_path)
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
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.wav')
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_path)
        video.close()
        return output_path

    def extract_frames(self, video_path: str, num_frames: int = 10) -> List:
        """Extract key frames spread evenly across the video."""
        import cv2
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
    # Segment selection to hit 40-50% of original duration
    # ------------------------------------------------------------------
    def _select_segments_for_target_duration(
        self,
        ranked_segments: List[Dict],
        video_duration: float,
        all_segments: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Choose segments whose total duration is ~TARGET_RATIO (45%) of the
        original video. Returns segments sorted chronologically.

        Strategy:
        1. Start with the highest-ranked (most important) segments.
        2. Keep adding until we reach TARGET_RATIO of original duration.
        3. If we overshoot, trim the last segment to fit exactly.
        4. Re-sort chronologically for natural playback order.
        """
        target_duration = video_duration * TARGET_RATIO
        target_min = video_duration * TARGET_RATIO_MIN
        target_max = video_duration * TARGET_RATIO_MAX

        # Work from ranked segments (highest relevance first)
        pool = list(ranked_segments)
        if not pool and all_segments:
            # Fallback: evenly spread segments from full list
            pool = list(all_segments)

        if not pool:
            return []

        selected = []
        accumulated = 0.0

        for seg in pool:
            start = seg.get("start", 0)
            end = seg.get("end", start + 2.0)
            seg_dur = end - start
            if seg_dur < MIN_CLIP_DURATION:
                continue

            remaining_budget = target_max - accumulated
            if remaining_budget <= MIN_CLIP_DURATION:
                break  # Budget exhausted

            if seg_dur > remaining_budget:
                # Trim this segment to exactly fill the remaining budget
                seg = dict(seg)
                seg["end"] = seg["start"] + remaining_budget
                seg_dur = remaining_budget

            selected.append(seg)
            accumulated += seg_dur

            if accumulated >= target_min:
                break  # Already in the 40-50% window — stop

        # If we didn't reach 40% with ranked segments, add more from the pool
        if accumulated < target_min and all_segments:
            # Add segments not already selected
            selected_starts = {s.get("start") for s in selected}
            extras = [s for s in all_segments if s.get("start") not in selected_starts]
            for seg in extras:
                if accumulated >= target_min:
                    break
                start = seg.get("start", 0)
                end = seg.get("end", start + 2.0)
                seg_dur = end - start
                if seg_dur < MIN_CLIP_DURATION:
                    continue
                remaining_budget = target_max - accumulated
                if seg_dur > remaining_budget:
                    seg = dict(seg)
                    seg["end"] = seg["start"] + remaining_budget
                    seg_dur = remaining_budget
                selected.append(seg)
                accumulated += seg_dur

        # Sort chronologically for natural playback
        selected.sort(key=lambda s: s.get("start", 0))

        logger.info(
            "Segment selection: %d clips, total %.1fs (%.0f%% of %.1fs original)",
            len(selected), accumulated, (accumulated / video_duration) * 100, video_duration,
        )
        return selected

    # ------------------------------------------------------------------
    # Main: create_summary_video (old API, kept for backward compat)
    # ------------------------------------------------------------------
    def create_summary_video(self, video_path: str, segments: List[Dict], output_path: str):
        """Create summary video from selected segments (clip-based)."""
        return self.create_highlight_video(video_path, segments, output_path)

    # ------------------------------------------------------------------
    # create_highlight_video — simple concatenation
    # ------------------------------------------------------------------
    def create_highlight_video(
        self,
        video_path: str,
        segments: List[Dict],
        output_path: str,
        title: str = "Video Highlights",
    ):
        """Stitch selected segments into a highlight reel."""
        try:
            source = VideoFileClip(video_path)
            clips = []

            for seg in segments[:20]:
                start, end = seg.get("start", 0), seg.get("end", 0)
                if end - start < MIN_CLIP_DURATION:
                    continue
                end = min(end, source.duration)
                try:
                    clip = source.subclipped(start, end) if MOVIEPY_V2 else source.subclip(start, end)
                    clips.append(clip)
                except Exception as e:
                    logger.warning("Skipping segment [%.1f-%.1f]: %s", start, end, e)

            if not clips:
                source.close()
                raise ValueError("No valid clips to stitch")

            final = concatenate_videoclips(clips, method="compose")
            self._write_video(final, output_path)
            final.close()
            source.close()
            return output_path
        except Exception as e:
            logger.error("Highlight video creation failed: %s", e)
            raise

    # ------------------------------------------------------------------
    # create_visual_summary — PRIMARY METHOD (40-50% duration)
    # ------------------------------------------------------------------
    def create_visual_summary(
        self,
        video_path: str,
        text_summary: str,
        key_points: List[str],
        output_path: str,
        video_title: str = "Video Summary",
        num_key_frames: int = 0,
        segments: Optional[List[Dict]] = None,
        all_segments: Optional[List[Dict]] = None,
    ) -> str:
        """
        Create a summary video that is ~40-50% of the original video's duration.

        Uses actual video clips from the source (preserving original audio),
        stitched together with a title slide and closing slide.
        """
        logger.info("Creating summary video for %s", video_path)

        # 1. Load source
        source = VideoFileClip(video_path)
        video_duration = source.duration
        has_audio = source.audio is not None
        duration_str = self._format_duration(video_duration)

        # 2. Select segments targeting 40-50% of total duration
        pool = segments or []
        selected = self._select_segments_for_target_duration(pool, video_duration, all_segments)

        if not selected:
            # Ultimate fallback: evenly spread clips covering ~45% of video
            logger.warning("No segments provided — using evenly-spread clips")
            target_dur = video_duration * TARGET_RATIO
            chunk = max(3.0, target_dur / 8)
            step = video_duration / 8
            selected = []
            for i in range(8):
                s = i * step
                e = min(video_duration, s + chunk)
                if e - s >= MIN_CLIP_DURATION:
                    selected.append({"start": s, "end": e})
            # Re-trim to target
            selected = self._select_segments_for_target_duration(selected, video_duration)

        # Compute expected summary duration (for title slide info)
        summary_duration = sum(
            min(seg.get("end", 0), source.duration) - seg.get("start", 0)
            for seg in selected
        ) + TITLE_SLIDE_DURATION + CLOSING_SLIDE_DURATION
        summary_duration_str = self._format_duration(summary_duration)

        # 3. Build clips list
        all_clips = []

        # --- Title slide ---
        title_arr = self._create_title_slide(video_title, duration_str, summary_duration_str)
        title_clip = _make_image_clip(title_arr, TITLE_SLIDE_DURATION)
        # Resize title slide to match source if needed
        if (source.w, source.h) != (title_arr.shape[1], title_arr.shape[0]):
            title_clip = _resize_clip(title_clip, (source.w, source.h))
        all_clips.append(title_clip)

        # --- Content clips ---
        content_clips_added = 0
        for seg in selected:
            start = seg.get("start", 0)
            end = min(seg.get("end", start + 3), source.duration)
            if end - start < MIN_CLIP_DURATION:
                continue
            try:
                clip = (
                    source.subclipped(start, end)
                    if MOVIEPY_V2
                    else source.subclip(start, end)
                )
                all_clips.append(clip)
                content_clips_added += 1
            except Exception as e:
                logger.warning("Skipping clip [%.1f-%.1f]: %s", start, end, e)

        if content_clips_added == 0:
            logger.error("No content clips could be extracted!")
            source.close()
            raise RuntimeError("Failed to extract any video clips for summary")

        # --- Closing slide ---
        closing_arr = self._create_closing_slide()
        closing_clip = _make_image_clip(closing_arr, CLOSING_SLIDE_DURATION)
        if (source.w, source.h) != (closing_arr.shape[1], closing_arr.shape[0]):
            closing_clip = _resize_clip(closing_clip, (source.w, source.h))
        all_clips.append(closing_clip)

        logger.info(
            "Concatenating %d clips (1 title + %d content + 1 closing)",
            len(all_clips), content_clips_added,
        )

        # 4. Concatenate and write
        final = concatenate_videoclips(all_clips, method="compose")

        logger.info(
            "Final summary video: %.1fs (original: %.1fs, ratio: %.0f%%)",
            final.duration, video_duration, (final.duration / video_duration) * 100,
        )

        write_kwargs = {
            "fps": FPS,
            "codec": "libx264",
            "preset": "ultrafast",
            "threads": 4,
            "bitrate": "1800k",
            "logger": None,
            "ffmpeg_params": ["-pix_fmt", "yuv420p", "-crf", "26"],
        }
        if has_audio:
            write_kwargs["audio_codec"] = "aac"
        else:
            write_kwargs["audio"] = False

        try:
            self._write_video(final, output_path, **write_kwargs)
        except Exception as write_err:
            logger.error("write_videofile failed: %s — retrying without audio", write_err)
            write_kwargs["audio"] = False
            write_kwargs.pop("audio_codec", None)
            self._write_video(final, output_path, **write_kwargs)

        final.close()
        source.close()
        logger.info("Summary video saved: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Write helper (handles MoviePy 1/2 API difference)
    # ------------------------------------------------------------------
    @staticmethod
    def _write_video(clip, output_path: str, **kwargs):
        """Write video file, filling in sensible defaults."""
        defaults = {
            "fps": FPS,
            "codec": "libx264",
            "preset": "ultrafast",
            "threads": 4,
            "logger": None,
            "ffmpeg_params": ["-pix_fmt", "yuv420p"],
        }
        defaults.update(kwargs)

        # MoviePy 2.x uses write_videofile the same way as 1.x
        clip.write_videofile(output_path, **defaults)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    @staticmethod
    def _format_duration(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    @staticmethod
    def _split_text_for_slides(text: str, max_chars_per_slide: int = 280) -> List[str]:
        if not text or not text.strip():
            return [""]
        sentences = []
        for s in text.replace("\n", " ").split(". "):
            s = s.strip()
            if s:
                sentences.append(s if s.endswith(".") else s + ".")
        if not sentences:
            return [text[i:i + max_chars_per_slide] for i in range(0, len(text), max_chars_per_slide)] or [text]
        chunks, current = [], ""
        for sentence in sentences:
            if current and len(current) + len(sentence) + 1 > max_chars_per_slide:
                chunks.append(current.strip())
                current = sentence
            else:
                current = (current + " " + sentence).strip()
        if current.strip():
            chunks.append(current.strip())
        return chunks or [text[:max_chars_per_slide]]


# Test
if __name__ == "__main__":
    processor = VideoProcessor()
    print("Video processor ready! MoviePy v2:", MOVIEPY_V2)
