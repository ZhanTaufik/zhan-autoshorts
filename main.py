"""
YouTube Shorts Automation Bot
Pipeline: Reddit → Script → TTS → Video → YouTube
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

from config import Config
from scraper import RedditScraper
from script_generator import ScriptGenerator
from tts import TTSEngine
from video_editor import VideoEditor
from youtube_uploader import YouTubeUploader

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ],
)
log = logging.getLogger(__name__)


def run_pipeline(dry_run: bool = False):
    """
    Full automation pipeline.
    Set dry_run=True to skip the YouTube upload step (useful for testing).
    """
    cfg = Config()
    cfg.ensure_dirs()

    log.info("═" * 60)
    log.info("  YouTube Shorts Bot  |  %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("═" * 60)

    # ── 1. Scrape Reddit ──────────────────────────────────────────────────────
    log.info("[1/5] Scraping Reddit …")
    scraper = RedditScraper(cfg)
    posts = scraper.fetch_posts(
        subreddits=cfg.SUBREDDITS,
        min_score=cfg.MIN_SCORE,
        limit=cfg.FETCH_LIMIT,
    )

    if not posts:
        log.warning("No posts found. Exiting.")
        return

    log.info("  → Found %d candidate posts", len(posts))

    # Filter already-processed posts
    processed = _load_processed(cfg.PROCESSED_FILE)
    posts = [p for p in posts if p["id"] not in processed]
    log.info("  → %d unprocessed posts remain", len(posts))

    if not posts:
        log.info("All posts already processed. Nothing to do.")
        return

    # Pick the best post
    post = posts[0]
    log.info("  → Selected: r/%s | score=%d | '%s'", post["subreddit"], post["score"], post["title"][:60])

    # ── 2. Generate Script ────────────────────────────────────────────────────
    log.info("[2/5] Generating Short script …")
    generator = ScriptGenerator(cfg)
    script = generator.generate(post)

    log.info("  → Script (%d chars): %s…", len(script["voiceover"]), script["voiceover"][:80])
    log.info("  → Title: %s", script["title"])
    log.info("  → Description snippet: %s…", script["description"][:60])

    # ── 3. Text-to-Speech ─────────────────────────────────────────────────────
    log.info("[3/5] Generating voiceover …")
    tts = TTSEngine(cfg)
    audio_path = cfg.TEMP_DIR / f"{post['id']}_voice.mp3"
    tts.synthesize(script["voiceover"], str(audio_path))
    log.info("  → Audio saved: %s", audio_path)

    # ── 4. Create Video ───────────────────────────────────────────────────────
    log.info("[4/5] Compositing video …")
    editor = VideoEditor(cfg)
    video_path = cfg.OUTPUT_DIR / f"{post['id']}_short.mp4"
    editor.create_short(
        audio_path=str(audio_path),
        output_path=str(video_path),
        title=script["title"],
        subtitles=script["subtitles"],
    )
    log.info("  → Video saved: %s", video_path)

    # ── 5. Upload to YouTube ──────────────────────────────────────────────────
    if dry_run:
        log.info("[5/5] DRY RUN — skipping YouTube upload")
        youtube_url = "https://youtube.com/shorts/DRY_RUN"
    else:
        log.info("[5/5] Uploading to YouTube …")
        uploader = YouTubeUploader(cfg)
        youtube_url = uploader.upload(
            video_path=str(video_path),
            title=script["title"],
            description=script["description"],
            tags=script["tags"],
        )
        log.info("  → Uploaded: %s", youtube_url)

    # ── Mark as processed ─────────────────────────────────────────────────────
    _save_processed(cfg.PROCESSED_FILE, post["id"], {
        "title": script["title"],
        "url": youtube_url,
        "processed_at": datetime.now().isoformat(),
    })

    log.info("═" * 60)
    log.info("  Done!  %s", youtube_url)
    log.info("═" * 60)

    return youtube_url


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_processed(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_processed(path: Path, post_id: str, meta: dict):
    data = _load_processed(path)
    data[post_id] = meta
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Bot")
    parser.add_argument("--dry-run", action="store_true", help="Skip YouTube upload")
    parser.add_argument(
        "--count", type=int, default=1, help="Number of Shorts to produce (default 1)"
    )
    args = parser.parse_args()

    for i in range(args.count):
        log.info("--- Short %d / %d ---", i + 1, args.count)
        run_pipeline(dry_run=args.dry_run)
