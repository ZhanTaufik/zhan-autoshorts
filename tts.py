"""
tts.py – Text-to-Speech engine.

Supports:
  - "openai"  → OpenAI TTS API (high quality, requires OPENAI_API_KEY)
  - "gtts"    → Google TTS (free, no key needed, slightly robotic)
  - "elevenlabs" → ElevenLabs API (premium, requires ELEVENLABS_API_KEY)
"""

import logging
import os
from pathlib import Path
from config import Config

log = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.engine = cfg.TTS_ENGINE.lower()

    def synthesize(self, text: str, output_path: str) -> str:
        """Convert text to speech and save as MP3. Returns output_path."""
        log.info("  TTS engine: %s", self.engine)

        if self.engine == "openai":
            self._synthesize_openai(text, output_path)
        elif self.engine == "elevenlabs":
            self._synthesize_elevenlabs(text, output_path)
        else:
            self._synthesize_gtts(text, output_path)

        if not Path(output_path).exists():
            raise RuntimeError(f"TTS failed – no file at {output_path}")

        size_kb = Path(output_path).stat().st_size // 1024
        log.info("  Audio: %s (%d KB)", output_path, size_kb)
        return output_path

    # ── OpenAI TTS ─────────────────────────────────────────────────────────────

    def _synthesize_openai(self, text: str, output_path: str):
        from openai import OpenAI

        client = OpenAI(api_key=self.cfg.OPENAI_API_KEY)
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice=self.cfg.OPENAI_TTS_VOICE,
            input=text,
            speed=1.1,   # slightly faster for Shorts
        )
        response.stream_to_file(output_path)

    # ── Google TTS (free) ──────────────────────────────────────────────────────

    def _synthesize_gtts(self, text: str, output_path: str):
        from gtts import gTTS
        import subprocess

        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(output_path)

        # Speed up by 10% with ffmpeg for a more energetic feel
        sped_path = output_path.replace(".mp3", "_fast.mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", output_path,
                 "-filter:a", "atempo=1.1",
                 sped_path],
                check=True, capture_output=True,
            )
            os.replace(sped_path, output_path)
        except Exception as e:
            log.warning("ffmpeg speed-up failed (using original): %s", e)

    # ── ElevenLabs ─────────────────────────────────────────────────────────────

    def _synthesize_elevenlabs(self, text: str, output_path: str):
        import requests

        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(r.content)
