"""
config.py – All settings for the YouTube Shorts bot.

Copy .env.example → .env and fill in your API keys.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


class Config:
    # ── Directories ───────────────────────────────────────────────────────────
    TEMP_DIR: Path = BASE_DIR / "temp"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    ASSETS_DIR: Path = BASE_DIR / "assets"          # put background videos here
    PROCESSED_FILE: Path = BASE_DIR / "processed.json"

    # ── Reddit (PRAW) ─────────────────────────────────────────────────────────
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "YTShortsBot/1.0")

    # Which subreddits to mine (override in .env as comma-separated list)
    _subreddits_env: str = os.getenv(
        "SUBREDDITS",
        "AskReddit,tifu,todayilearned,LifeProTips,NoStupidQuestions"
    )
    SUBREDDITS: list[str] = [s.strip() for s in _subreddits_env.split(",")]

    MIN_SCORE: int = int(os.getenv("MIN_SCORE", "1000"))   # minimum upvotes
    FETCH_LIMIT: int = int(os.getenv("FETCH_LIMIT", "25")) # posts to inspect

    # ── Anthropic / Claude ────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    MAX_VOICEOVER_CHARS: int = 900   # ~60s spoken at ~150 wpm

    # ── TTS engine: "openai" | "gtts" ────────────────────────────────────────
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "gtts")   # free default
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_TTS_VOICE: str = os.getenv("OPENAI_TTS_VOICE", "onyx")   # alloy/echo/fable/onyx/nova/shimmer

    # ── Video settings ────────────────────────────────────────────────────────
    VIDEO_WIDTH: int = 1080
    VIDEO_HEIGHT: int = 1920   # 9:16 portrait
    VIDEO_FPS: int = 30

    # Font used for subtitles / title card
    SUBTITLE_FONT: str = os.getenv("SUBTITLE_FONT", "Arial-Bold")
    SUBTITLE_FONTSIZE: int = 60
    SUBTITLE_COLOR: str = "white"
    SUBTITLE_STROKE_COLOR: str = "black"
    SUBTITLE_STROKE_WIDTH: int = 3

    # Path to a background video clip (loops if shorter than voiceover).
    # Leave empty to auto-download a free one from Pexels.
    BACKGROUND_VIDEO: str = os.getenv("BACKGROUND_VIDEO", "")
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")  # for auto-download

    # ── YouTube (OAuth 2.0) ───────────────────────────────────────────────────
    YOUTUBE_CLIENT_SECRETS: str = os.getenv(
        "YOUTUBE_CLIENT_SECRETS", str(BASE_DIR / "client_secrets.json")
    )
    YOUTUBE_TOKEN_FILE: str = os.getenv(
        "YOUTUBE_TOKEN_FILE", str(BASE_DIR / "youtube_token.json")
    )
    YOUTUBE_CATEGORY_ID: str = "22"   # People & Blogs; change to "24" for Entertainment
    YOUTUBE_PRIVACY: str = os.getenv("YOUTUBE_PRIVACY", "public")   # public/unlisted/private
    YOUTUBE_MADE_FOR_KIDS: bool = False

    def ensure_dirs(self):
        for d in (self.TEMP_DIR, self.OUTPUT_DIR, self.ASSETS_DIR):
            d.mkdir(parents=True, exist_ok=True)
