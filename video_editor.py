"""
video_editor.py – Composites a YouTube Short.

Steps:
  1. Load background video (loops if too short, downloads from Pexels if missing).
  2. Load voiceover audio and match video duration to it.
  3. Overlay animated subtitle chunks.
  4. Add a semi-transparent title card at the top.
  5. Export 1080×1920 MP4 @ 30fps.
"""

import logging
import os
import random
import subprocess
from pathlib import Path

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
    afx,
)
from config import Config

log = logging.getLogger(__name__)

W, H = 1080, 1920   # 9:16


class VideoEditor:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def create_short(
        self,
        audio_path: str,
        output_path: str,
        title: str,
        subtitles: list[dict],
    ):
        """
        Compose and export the Short.

        subtitles: [{"text": "...", "duration": 2.5}, ...]
        """
        # ── Audio ─────────────────────────────────────────────────────────────
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        log.info("  Audio duration: %.1fs", duration)

        # ── Background ────────────────────────────────────────────────────────
        bg = self._get_background(duration)

        # ── Subtitles ─────────────────────────────────────────────────────────
        subtitle_clips = self._build_subtitles(subtitles, duration)

        # ── Title card ────────────────────────────────────────────────────────
        title_clip = self._build_title_card(title, duration)

        # ── Compose ───────────────────────────────────────────────────────────
        layers = [bg] + subtitle_clips + [title_clip]
        video = CompositeVideoClip(layers, size=(W, H))
        video = video.set_audio(audio)
        video = video.set_duration(duration)

        # ── Export ────────────────────────────────────────────────────────────
        log.info("  Exporting video → %s", output_path)
        video.write_videofile(
            output_path,
            fps=self.cfg.VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            threads=4,
            preset="fast",
            logger=None,   # suppress moviepy progress spam
        )

        # Clean up
        audio.close()
        video.close()

    # ── Background video ───────────────────────────────────────────────────────

    def _get_background(self, duration: float) -> VideoFileClip:
        bg_path = self._resolve_background_path()
        clip = VideoFileClip(bg_path, audio=False)

        # Crop / resize to 9:16
        clip = self._crop_to_portrait(clip)

        # Loop until long enough
        if clip.duration < duration:
            loops = int(duration / clip.duration) + 1
            clip = concatenate_videoclips([clip] * loops)

        clip = clip.subclip(0, duration)

        # Darken so subtitles are readable
        clip = clip.fx(afx.multiply_color, 0.55)

        return clip.set_position("center")

    def _resolve_background_path(self) -> str:
        """Return a background video path, downloading one if needed."""
        # 1. User-specified path
        if self.cfg.BACKGROUND_VIDEO and Path(self.cfg.BACKGROUND_VIDEO).exists():
            return self.cfg.BACKGROUND_VIDEO

        # 2. Pick a random video from assets/
        assets = list(Path(self.cfg.ASSETS_DIR).glob("*.mp4"))
        if assets:
            chosen = random.choice(assets)
            log.info("  Background: %s", chosen.name)
            return str(chosen)

        # 3. Download from Pexels
        if self.cfg.PEXELS_API_KEY:
            return self._download_pexels_video()

        raise FileNotFoundError(
            "No background video found. Add an MP4 to assets/ or set PEXELS_API_KEY."
        )

    def _download_pexels_video(self) -> str:
        import requests

        queries = ["minecraft parkour", "satisfying", "subway surfers", "nature timelapse", "city night"]
        query = random.choice(queries)

        headers = {"Authorization": self.cfg.PEXELS_API_KEY}
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": query, "orientation": "portrait", "per_page": 10},
            timeout=15,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            raise RuntimeError("Pexels returned no videos for query: " + query)

        video = random.choice(videos)
        # Pick the highest-res file
        files = sorted(video["video_files"], key=lambda f: f.get("width", 0), reverse=True)
        url = files[0]["link"]

        dest = self.cfg.ASSETS_DIR / f"pexels_{video['id']}.mp4"
        if not dest.exists():
            log.info("  Downloading background from Pexels: %s", url)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

        return str(dest)

    # ── Cropping ───────────────────────────────────────────────────────────────

    @staticmethod
    def _crop_to_portrait(clip: VideoFileClip) -> VideoFileClip:
        """Resize and centre-crop to 1080×1920."""
        target_ratio = W / H
        src_ratio = clip.w / clip.h

        if src_ratio > target_ratio:
            # Wider than needed → crop width
            new_w = int(clip.h * target_ratio)
            x1 = (clip.w - new_w) // 2
            clip = clip.crop(x1=x1, width=new_w)
        elif src_ratio < target_ratio:
            # Taller than needed → crop height
            new_h = int(clip.w / target_ratio)
            y1 = (clip.h - new_h) // 2
            clip = clip.crop(y1=y1, height=new_h)

        return clip.resize((W, H))

    # ── Subtitles ──────────────────────────────────────────────────────────────

    def _build_subtitles(self, subtitles: list[dict], total_duration: float) -> list:
        clips = []
        current_time = 0.0

        for chunk in subtitles:
            text = chunk.get("text", "").upper()
            dur = float(chunk.get("duration", 2.5))

            if current_time >= total_duration:
                break

            # Clamp duration so we don't exceed total
            dur = min(dur, total_duration - current_time)

            txt_clip = (
                TextClip(
                    text,
                    fontsize=self.cfg.SUBTITLE_FONTSIZE,
                    font=self.cfg.SUBTITLE_FONT,
                    color=self.cfg.SUBTITLE_COLOR,
                    stroke_color=self.cfg.SUBTITLE_STROKE_COLOR,
                    stroke_width=self.cfg.SUBTITLE_STROKE_WIDTH,
                    method="caption",
                    size=(W - 80, None),
                    align="center",
                )
                .set_start(current_time)
                .set_duration(dur)
                .set_position(("center", int(H * 0.62)))
            )

            # Fade in/out
            txt_clip = txt_clip.crossfadein(0.15).crossfadeout(0.15)
            clips.append(txt_clip)
            current_time += dur

        return clips

    # ── Title card ─────────────────────────────────────────────────────────────

    def _build_title_card(self, title: str, duration: float):
        """Semi-transparent pill at the top showing the video title."""
        max_chars = 60
        display_title = title[:max_chars] + ("…" if len(title) > max_chars else "")

        txt = TextClip(
            display_title,
            fontsize=42,
            font=self.cfg.SUBTITLE_FONT,
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(W - 100, None),
            align="center",
        ).set_position(("center", 120)).set_duration(duration)

        return txt
